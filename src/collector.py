#!/usr/bin/env python
# -*- coding: utf-8 -*-

################################################################################
#
# caos-collector - CAOS collector
#
# Copyright © 2016 INFN - Istituto Nazionale di Fisica Nucleare (Italy)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
# Author: Fabrizio Chiarello <fabrizio.chiarello@pd.infn.it>
#
################################################################################

import argparse
import datetime
import os
import sys
import signal
import StringIO

from _version import __version__
import caos_api
import ceilometer
import log
import utils
import cfg
import pollsters


from keystoneclient.auth.identity import v3
from keystoneauth1 import session
from keystoneclient import client as keystone_client

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor


DEFAULT_CFG_FILE = '/etc/caos/collector.conf'


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
                    default=DEFAULT_CFG_FILE,
                    help='configuration file')

parser.add_argument('-f', '--force',
                    action='store_const',
                    const=True,
                    help='Enable overwriting existing samples.')

subparsers = parser.add_subparsers(dest="cmd",
                                   help='sub commands')

parser_run = subparsers.add_parser('run', help='run scheduled collection')

parser_shot = subparsers.add_parser('shot', help='shot collection')

parser_shot.add_argument('-s', '--start',
                         dest='start', metavar='TIMESTAMP',
                         nargs='?',
                         default=utils.format_date(datetime.datetime.utcnow()),
                         help='Perform shot collection from TIMESTAMP (default to now)')

parser_shot.add_argument('-r', '--repeat',
                         dest='repeat', metavar='N',
                         nargs='?',
                         default=1,
                         help='Repeat N times (default to 1)')

parser_shot.add_argument('-P', '--project',
                         dest='project', metavar='PROJECT',
                         nargs='?',
                         default='ALL',
                         help='Collect only project PROJECT (default to ALL)')

parser_shot.add_argument('-m', '--metric',
                         dest='metric', metavar='METRIC',
                         nargs='?',
                         default='ALL',
                         help='Collect only metric METRIC (default to ALL)')

parser_shot.add_argument('-p', '--period',
                         dest='period', metavar='PERIOD',
                         nargs='?',
                         default='ALL',
                         help='Collect only period PERIOD (default to ALL)')



def get_keystone_session():
    os_envs = {
        'username'            : cfg.KEYSTONE_USERNAME,
        'password'            : cfg.KEYSTONE_PASSWORD,
        'auth_url'            : cfg.KEYSTONE_AUTH_URL,
        'project_id'          : cfg.KEYSTONE_PROJECT_ID,
        'project_name'        : cfg.KEYSTONE_PROJECT_NAME,
        'domain_id'           : cfg.KEYSTONE_DOMAIN_ID,
        'domain_name'         : cfg.KEYSTONE_DOMAIN_NAME,
        'user_domain_id'      : cfg.KEYSTONE_USER_DOMAIN_ID,
        'user_domain_name'    : cfg.KEYSTONE_USER_DOMAIN_NAME,
        'project_domain_id'   : cfg.KEYSTONE_PROJECT_DOMAIN_ID,
        'project_domain_name' : cfg.KEYSTONE_PROJECT_DOMAIN_NAME
    }

    auth = v3.Password(**os_envs)
    return session.Session(auth=auth, verify=cfg.KEYSTONE_CACERT)


def update_projects(keystone_session):
    # get projects from keystone
    keystone = keystone_client.Client(session=keystone_session,
                                      version=cfg.KEYSTONE_API_VERSION)

    logger.debug("Querying projects from keystone...")
    if keystone.version == 'v3':
        keystone_projects = keystone.projects.list()
    elif keystone.version == 'v2':
        keystone_projects = keystone.tenants.list()
    else:
        raise RuntimeError("Unknown keystoneclient version: '%s'" % keystone.version)
    keystone_projects = dict((p.id, p.name) for p in keystone_projects)

    # get known projects
    my_projects = caos_api.projects()

    for id in keystone_projects:
        name = keystone_projects[id]
        if id not in my_projects:
            logger.info("Adding new project %s (%s)" % (id, name))
            caos_api.add_project(id, name)
        elif not my_projects[id] == name:
            logger.info("Updating project %s (%s)" % (id, name))
            caos_api.set_project(id, name)

    return keystone_projects.keys()


def update_metrics():
    metrics = caos_api.metrics()
    enabled_metrics = cfg.METRICS

    for m in enabled_metrics:
        if m not in metrics:
            logger.info("Adding new metric %s" % m)
            caos_api.add_metric(name=m, type=enabled_metrics[m]['type'])
    return enabled_metrics


def update_series(projects, metrics):
    series = caos_api.series()
    enabled_series = cfg.SERIES

    for project_id in projects:
        for s in enabled_series:
            metric_name = s['metric_name']
            period = s['period']
            if not caos_api.series(project_id=project_id,
                                   metric_name=metric_name,
                                   period=period):
                logger.info("Adding new series %s/%d for project %s" % (metric_name, period, project_id))
                caos_api.create_series(project_id=project_id,
                                       metric_name=metric_name,
                                       period=period)


def collect_real(metric_name, series, start, end, force):
    logger.info("Collecting from %s to %s", start, end)

    pollster = pollsters.get_pollster(metric_name)
    pollster_instance = pollster(series=series, start=start, end=end)
    sample = pollster_instance.run(force)
    return sample


def report_alive(scheduler):
    logger.info("Collector is alive")

    output = StringIO.StringIO()
    scheduler.print_jobs(out=output)
    logger.info(output.getvalue())
    output.close()


def collect(period_name, period, misfire_grace_time):
    logger.info("Starting collection for period %s (%ds)" %(period_name, period))

    # get a keystone session
    keystone_session = get_keystone_session()

    # update the known projects
    projects = update_projects(keystone_session)

    # update the metrics (this will not reread the config file)
    metrics = update_metrics()

    force = cfg.CFG['force']
    shot = cfg.CFG['shot']
    if shot:
        shot_metric = shot['metric']
        if shot_metric != 'ALL':
            if not shot_metric in metrics:
                logger.error("Unknown shot metric %s (use ALL or one of %s)" % (shot_metric, metrics.keys()))
                sys.exit(1)
            metrics = {shot_metric: metrics[shot_metric]}

        shot_project = shot['project']
        if shot_project != 'ALL':
            if not shot_project in projects:
                logger.error("Unknown shot project %s (use ALL or one of %s)" % (shot_project, projects.keys()))
                sys.exit(1)
            projects = {shot_project: shot_project}

    # update the series (in case a new project has been added)
    update_series(projects, metrics)

    for project_id in projects:
        for metric_name in metrics:
            series = caos_api.series(project_id=project_id,
                                     metric_name=metric_name,
                                     period=period)[0]
            series_id = series['id']
            last_timestamp = series['last_timestamp']

            # If we have at least on period between now (end) and
            # last_timestamp, then we collect (also respecting
            # misfire_grace_time).
            #
            # If the --shot option is given, then we ignore those checks.
            #
            # If the --force option is given, we permit overwriting
            # existing samples.

            if not last_timestamp:
                # this happens when the series has no data
                logger.info("No previous measurements for project %s, metric %s, period %d", project_id, metric_name, period)

                # set to epoch
                last_timestamp = utils.EPOCH

            if shot:
                logger.info("Doing %d shots starting at %s for project %s, metric %s, period %d", shot['N'], shot['start'], project_id, metric_name, period)
                next_timestamp = shot['start']
            else:
                next_timestamp = last_timestamp + datetime.timedelta(seconds=period)

            now = datetime.datetime.utcnow()
            if next_timestamp > now:
                # the series is already update
                logger.info("Series %d is uptodate", series['id'])
                continue


            if not shot and misfire_grace_time > period:
                # we respect a misfire_grace_time greater then the period
                if next_timestamp < now - datetime.timedelta(seconds=misfire_grace_time):
                    logger.info("Dropping history collection due to misfire_grace_time=%d" % misfire_grace_time)
                    next_timestamp = now - datetime.timedelta(seconds=misfire_grace_time)


            # ask for the time grid
            time_grid = caos_api.series_grid(series_id=series_id,
                                             from_date=next_timestamp)

            if shot:
                N = shot['N']
                time_grid = time_grid[0:N]

            for ts in time_grid:
                end = ts
                start = ts - datetime.timedelta(seconds=period)

                # check if sample already exists:
                s = caos_api.samples(series_id=series_id,
                                     timestamp=ts)

                if s and not force:
                    logger.debug("Sample already exists, skipping")
                else:
                    sample = collect_real(metric_name=metric_name,
                                          series=series,
                                          start=start,
                                          force=force,
                                          end=end)

                    if force:
                        logger.warn("FORCE: sample %s overwritten by %s", s, sample)


def collect_job(*args, **kwargs):
    try:
        ok = caos_api.refresh_token()
    except caos_api.ConnectionError as e:
        logger.warn("API connection problems: %s. Retrying at next polling time.", e)
        return
    except caos_api.AuthError as e:
        logger.warn("API auth problems: %s. Retrying at next polling time.", e)
        return
    if not ok:
        logger.warn("API auth problems. Retrying at next polling time.")
        return

    try:
        collect(*args, **kwargs)
    except ceilometer.ConnectionError as e:
        logger.warn("Got mongo connection problems: %s. Retrying at next polling time.", e)

    ceilometer.disconnect()


def setup_scheduler(periods):
    log.setup_apscheduler_logger()
    scheduler = BlockingScheduler(
        timezone="utc",
        executors={
            'default': ThreadPoolExecutor(1)})

    # the special alive job
    report_alive_period = cfg.SCHEDULER_REPORT_ALIVE_PERIOD
    logger.info("Registering report_alive job every %ds " % report_alive_period)
    scheduler.add_job(func=report_alive,

                      # trigger that determines when func is called
                      trigger='interval',
                      seconds=report_alive_period,

                      name="report_alive",
                      kwargs={
                          "scheduler": scheduler,
                      },

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

    misfire_grace_time = cfg.COLLECTOR_MISFIRE_GRACE_TIME
    for name in periods:
        period = periods[name]
        logger.info("Registering collect job for period %s (%ds)" %(name, period))

        scheduler.add_job(func=collect_job,

                          # trigger that determines when func is called
                          trigger='interval',
                          seconds=period,

                          name=name,
                          kwargs={
                              "period_name": name,
                              "period": period,
                              "misfire_grace_time": misfire_grace_time
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


def run_shot(args):
    logger.info("SHOT %s", args)
    shot = {
        'start': utils.parse_date(args.start),
        'N': int(args.repeat),
        'project': args.project,
        'period': args.period,
        'metric': args.metric
    }

    assert(shot['N'] > 0)
    cfg.CFG['shot'] = shot

    periods = cfg.PERIODS

    shot_period = shot['period']
    if shot_period != 'ALL':
        if not shot_period in periods:
            logger.error("Unknown shot period %s (use ALL or one of %s)" % (shot_period, periods.keys()))
            sys.exit(1)
        periods = {shot_period: periods[shot_period]}

    for name in periods:
        period = periods[name]
        kwargs={
            "period_name": name,
            "period": period,
            "misfire_grace_time": None
        }

        collect_job(**kwargs)


def main():
    args = parser.parse_args()
    cfg_file = args.cfg_file
    cfg.read(cfg_file)
    cfg.dump()
    log.setup_file_handlers()

    caos_api.initialize()
    try:
        logger.info("Checking API connectivity...")
        status = caos_api.status()
        logger.info("API version %s is in status '%s'", status['version'], status['status'])
    except caos_api.ConnectionError as e:
        logger.error("Cannot connect to API. Exiting....")
        sys.exit(1)

    try:
        logger.info("Checking API auth...")
        ok = caos_api.refresh_token()
        if not ok:
            logger.error("Cannot authenticate to API. Exiting...")
            sys.exit(1)
    except caos_api.AuthError as e:
        logger.error("Cannot authenticate to API: %s. Exiting...", e)
        sys.exit(1)


    cfg.CFG['force'] = None
    force = args.force
    if force:
        logger.info("FORCE COLLECTION ENABLED")
        logger.warn("FORCE WILL OVERWRITE EXISTING DATA!!!!")
        answer = raw_input("Are you sure? Type YES (uppercase) to go on: ")
        if not answer == "YES":
            return
        else:
            cfg.CFG['force'] = force

    try:
        ceilometer.initialize()
    except ceilometer.ConnectionError as e:
        logger.error("Error: %s. Check your mongodb setup. Exiting...", e)
        sys.exit(1)

    cfg.CFG['shot'] = None
    cmd = args.cmd
    if cmd == 'shot':
        run_shot(args)
        sys.exit(0)
    assert(cmd != 'shot')

    assert(cmd == 'run')

    periods = cfg.PERIODS
    scheduler = setup_scheduler(periods=periods)

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
