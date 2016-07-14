#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: collector.py
# Created: 2016-06-29T14:32:26+0200
# Time-stamp: <2016-07-14T15:09:46cest>
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
import ConfigParser
import os
import sys
import signal

from _version import __version__
from store import Store
from ceilometer import Ceilometer
import log

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


def get_cfg_option(section, option=None, type=None):
    if not config.has_section(section):
        raise SystemError("No [%s] option in config file." % section)

    if option and not config.has_option(section, option):
        raise SystemError("No [%s]/%s option in config file." % (section, option))

    if not option:
        return config.options(section)

    if type:
        fun = getattr(config, "get%s" % type)
    else:
        fun = getattr(config, "get")
    return fun(section, option)

config = ConfigParser.RawConfigParser()


def get_os_envs(opts):
    return dict((opt, get_cfg_option("keystone", opt)) for opt in opts)


def get_keystone_session():
    os_envs = get_os_envs([
        'username',
        'password',
        'auth_url',
        'project_id',
        'user_domain_id',
    ])

    auth = v3.Password(**os_envs)
    return session.Session(auth=auth, verify=get_cfg_option('keystone', 'cacert'))


def update_projects(keystone_session, store):
    # get projects from keystone
    keystone = keystone_client.Client(session=keystone_session)

    logger.debug("Querying projects from keystone...")
    # keystone_projects = keystone.projects.list()
    keystone_projects = keystone.tenants.list()
    keystone_projects = dict((p.id, p.name) for p in keystone_projects)

    # get known projects
    my_projects = store.projects()

    for id in keystone_projects:
        name = keystone_projects[id]
        if id not in my_projects:
            logger.debug("Adding new project %s (%s)" % (id, name))
            store.add_project(id, name)
        elif not my_projects[id] == name:
            logger.debug("Updating project %s (%s)" % (id, name))
            store.set_project(id, name)

    return keystone_projects.keys()


def get_metrics_cfg():
    ret = {}
    for s in config.sections():
        PREFIX = 'metric/'
        if s.startswith(PREFIX):
            _, name = s.split('/')
            ret[name] = {
                "type": get_cfg_option(s, 'type')
            }
    return ret


def update_metrics(store):
    metrics = store.metrics()
    enabled_metrics = get_metrics_cfg()

    for m in enabled_metrics:
        if m not in metrics:
            logger.info("Adding new metric %s" % m)
            store.add_metric(name=m, type=m['type'])
    return enabled_metrics


def get_periods_cfg():
    periods = get_cfg_option('periods')
    return dict((p, get_cfg_option('periods', p, 'int')) for p in periods)


def get_series_cfg():
    periods = get_periods_cfg()
    metrics = get_metrics_cfg()

    ret = []
    for s in config.sections():
        PREFIX = 'series/'
        if s.startswith(PREFIX):
            _, metric_name, period = s.split('/')
            ret.append({
                "metric_name": metric_name,
                "period": periods[period],
                "ttl": get_cfg_option(s, 'ttl', 'int')})
    return ret


def update_series(projects, metrics, store):
    series = store.series()
    enabled_series = get_series_cfg()

    for project_id in projects:
        for s in enabled_series:
            metric_name = s['metric_name']
            period = s['period']
            if not store.series_by(project_id=project_id,
                                   metric_name=metric_name,
                                   period=period):
                logger.info("Adding new series %s/%d for project %s" % (metric_name, period, project_id))
                store.create_series(project_id=project_id,
                                    metric_name=metric_name,
                                    period=period)


from pollsters import CPUPollster
pollsters = {
    'cpu': CPUPollster
}


def report_alive():
    logger.info("Collector is alive")


def collect(period_name, period):
    logger.info("Starting collection for period %s (%ds)" %(period_name, period))


def main():
    args = parser.parse_args()
    cfg_file = args.cfg_file
    logger.info("Reading configuration file: %s." % cfg_file)
    config.read(cfg_file)

    db_connection = get_cfg_option('db', 'connection')
    store_api_url = get_cfg_option('store', 'api-url')

    store = Store(store_api_url)

    keystone_session = get_keystone_session()
    projects = update_projects(keystone_session, store)

    metrics = update_metrics(store)
    update_series(projects, metrics, store)
    ceilometer = Ceilometer(db_connection)


    # configure the scheduler
    periods = get_periods_cfg()

    log.setup_apscheduler_logger()
    scheduler = BlockingScheduler(
        timezone="utc",
        executors={
            'default': ThreadPoolExecutor(1)})

    # the special alive job
    report_alive_period = get_cfg_option("scheduler", "report_alive_period", 'int')
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
                              "period": period},

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
