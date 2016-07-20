#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: collector.py
# Created: 2016-06-29T14:32:26+0200
# Time-stamp: <2016-07-20T09:39:10cest>
# Author: Fabrizio Chiarello <fabrizio.chiarello@pd.infn.it>
#
# Copyright © 2016 by Fabrizio Chiarello
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
######################################################################

import argparse
import datetime
import os
import sys
import signal

from _version import __version__
import apistorage
import ceilometer
import log
import utils
import cfg

from keystoneclient.auth.identity import v3
from keystoneauth1 import session
# import keystoneclient.v3.client as keystone_client
import keystoneclient.v2_0.client as keystone_client

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor


log.setup_logger()
logger = log.get_logger()
logger.info("Logger setup.")

# CLI ARGs
parser = argparse.ArgumentParser(description='Data collector for CAOS-NG.',
                                 add_help=True)

parser.add_argument('-v', '--version', action='version',
                    version='%(prog)s {version}'.format(version=__version__))

parser.add_argument('-c', '--config',
                    dest='cfg_file', metavar='FILE',
                    default='collector.conf',
                    help='configuration file')

parser.add_argument('-s', '--single-shot',
                    dest='single_shot', metavar='TIMESTAMP',
                    nargs='?',
                    const=utils.format_date(datetime.datetime.utcnow()),
                    help='Perform a single shot collection')

parser.add_argument('-f', '--force',
                    action='store_const',
                    const=True,
                    help='Force collection of data')


def get_keystone_session():
    os_envs = cfg.get_os_envs([
        'username',
        'password',
        'auth_url',
        'project_id',
        'user_domain_id',
    ])

    auth = v3.Password(**os_envs)
    return session.Session(auth=auth, verify=cfg.get('keystone', 'cacert'))


def update_projects(keystone_session):
    # get projects from keystone
    keystone = keystone_client.Client(session=keystone_session)

    logger.debug("Querying projects from keystone...")
    # keystone_projects = keystone.projects.list()
    keystone_projects = keystone.tenants.list()
    keystone_projects = dict((p.id, p.name) for p in keystone_projects)

    # get known projects
    my_projects = apistorage.projects()

    for id in keystone_projects:
        name = keystone_projects[id]
        if id not in my_projects:
            logger.info("Adding new project %s (%s)" % (id, name))
            apistorage.add_project(id, name)
        elif not my_projects[id] == name:
            logger.info("Updating project %s (%s)" % (id, name))
            apistorage.set_project(id, name)

    return keystone_projects.keys()


def update_metrics():
    metrics = apistorage.metrics()
    enabled_metrics = cfg.get_metrics()

    for m in enabled_metrics:
        if m not in metrics:
            logger.info("Adding new metric %s" % m)
            apistorage.add_metric(name=m, type=enabled_metrics[m]['type'])
    return enabled_metrics


def update_series(projects, metrics):
    series = apistorage.series()
    enabled_series = cfg.get_series()

    for project_id in projects:
        for s in enabled_series:
            metric_name = s['metric_name']
            period = s['period']
            if not apistorage.series(project_id=project_id,
                                     metric_name=metric_name,
                                     period=period):
                logger.info("Adding new series %s/%d for project %s" % (metric_name, period, project_id))
                apistorage.create_series(project_id=project_id,
                                         metric_name=metric_name,
                                         period=period)


from pollsters import CPUPollster
pollsters = {
    'cpu': CPUPollster
}


def collect_real(metric_name, series, start, end, force):
    logger.info("Collecting from %s to %s", start, end)

    pollster = pollsters[metric_name]
    pollster_instance = pollster(series=series, start=start, end=end)
    last_timestamp = pollster_instance.run(force)
    return last_timestamp


def report_alive():
    logger.info("Collector is alive")


def collect(period_name, period, misfire_grace_time, force=False, single_shot=None):
    logger.info("Starting collection for period %s (%ds)" %(period_name, period))

    # get a keystone session
    keystone_session = get_keystone_session()

    # update the known projects
    projects = update_projects(keystone_session)

    # update the metrics (this will not reread the config file)
    metrics = update_metrics()

    # update the series (in case a new project has been added)
    update_series(projects, metrics)

    metrics = ['cpu',]
    projects = ['b38a0dab349e42bdbb469274b20a91b4',]
    for project_id in projects:
        for metric_name in metrics:
            series = apistorage.series(project_id=project_id,
                                       metric_name=metric_name,
                                       period=period)[0]

            last_timestamp = series['last_timestamp']
            end = datetime.datetime.utcnow()

            if single_shot:
                end = single_shot
                start = end - datetime.timedelta(seconds=period)

                last_timestamp = collect_real(metric_name=metric_name,
                                              series=series,
                                              start=start,
                                              end=end,
                                              force=force)
                return

            if not last_timestamp:
                # this happens when the series has no data
                logger.info("No previous measurements for project %s, metric %s, period %d", project_id, metric_name, period)

                # set to epoch
                last_timestamp = datetime.datetime(year=1970, month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=None)


            if last_timestamp < end-datetime.timedelta(seconds=misfire_grace_time):
                # we don't want to go too much back in history, set a sane starting point
                logger.info("Going back in history")

                last_timestamp = end - datetime.timedelta(seconds=misfire_grace_time)


            if last_timestamp < end - datetime.timedelta(seconds=period):
                # it could go back in history
                time_grid = apistorage.series_grid(series_id=series['id'],
                                                   start_date=last_timestamp)

                for ts in time_grid:
                    end = ts
                    start = ts - datetime.timedelta(seconds=period)

                    last_timestamp = collect_real(metric_name=metric_name,
                                                  series=series,
                                                  start=start,
                                                  end=end)


            else:
                # the series is already update
                logger.info("Series %d is uptodate", series['id'])
                return


def setup_scheduler(periods, force):
    log.setup_apscheduler_logger()
    scheduler = BlockingScheduler(
        timezone="utc",
        executors={
            'default': ThreadPoolExecutor(1)})

    # the special alive job
    report_alive_period = cfg.get("scheduler", "report_alive_period", 'int')
    logger.info("Registering report_alive job every %ds " % report_alive_period)
    scheduler.add_job(func=report_alive,

                      # trigger that determines when func is called
                      trigger='interval',
                      seconds=report_alive_period,

                      name="report_alive",

                      # seconds after the designated runtime that
                      # the job is still allowed to be run
                      misfire_grace_time=int(round(report_alive_period/10)),

                      # run once instead of many times if the
                      # scheduler determines that the job should
                      # be run more than once in succession
                      coalesce=True,

                      # maximum number of concurrently running
                      # instances allowed for this job
                      max_instances=1,

                      # when to first run the job, regardless of the
                      # trigger (pass None to add the job as paused)
                      next_run_time=datetime.datetime.utcnow())

    misfire_grace_time = cfg.get("collector", "misfire_grace_time", "int")
    for name in periods:
        period = periods[name]
        logger.info("Registering collect job for period %s (%ds)" %(name, period))

        scheduler.add_job(func=collect,

                          # trigger that determines when func is called
                          trigger='interval',
                          seconds=period,

                          name=name,
                          kwargs={
                              "period_name": name,
                              "period": period,
                              "misfire_grace_time": misfire_grace_time,
                              "force": force
                          },

                          # seconds after the designated runtime that
                          # the job is still allowed to be run
                          misfire_grace_time=int(round(period/10)),

                          # run once instead of many times if the
                          # scheduler determines that the job should
                          # be run more than once in succession
                          coalesce=True,

                          # maximum number of concurrently running
                          # instances allowed for this job
                          max_instances=1,

                          # when to first run the job, regardless of
                          # the trigger (pass None to add the job as
                          # paused)
                          next_run_time=datetime.datetime.utcnow())

    return scheduler

def main():
    args = parser.parse_args()
    cfg_file = args.cfg_file
    logger.info("Reading configuration file: %s." % cfg_file)
    cfg.read(cfg_file)

    mongodb = cfg.get('ceilometer', 'mongodb')
    store_api_url = cfg.get('store', 'api-url')

    apistorage.initialize(store_api_url)
    ceilometer.initialize(mongodb)

    # configure the scheduler
    periods = cfg.get_periods()

    force = args.force
    if force:
        logger.info("FORCING COLLECTION")

    single_shot = args.single_shot
    if single_shot:
        logger.info("SINGLE SHOT %s", single_shot)

        misfire_grace_time = cfg.get("collector", "misfire_grace_time", "int")
        for name in periods:
            period = periods[name]
            kwargs={
                "period_name": name,
                "period": period,
                "misfire_grace_time": misfire_grace_time,
                "force": force,
                "single_shot": utils.parse_date(single_shot)
            }

            collect(**kwargs)

        return

    scheduler = setup_scheduler(periods=periods, force=force)

    def sigterm_handler(_signo, _stack_frame):
        # Raises SystemExit(0):
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    # this is blocking
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info('Got SIGTERM! Terminating...')
        scheduler.shutdown(wait=False)


if __name__ == "__main__":
    main()
