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

import datetime

import caos_api
import ceilometer
import log
import utils
import cfg
import pollsters
import openstack
import scheduler

logger = log.get_logger()


def initialize():
    logger.info("Initializing collector...")
    periods = cfg.PERIODS
    setup_scheduler(periods=periods)


def update_projects():
    # get projects from keystone
    keystone_projects = openstack.projects()

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




def collect(period_name, period, misfire_grace_time):
    logger.info("Starting collection for period %s (%ds)" %(period_name, period))

    # update the known projects
    projects = update_projects()

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
                                     period=period)
            if not series:
                logger.info('Skipping disabled series %s/%s for project %s', metric_name, period, project_id)
                continue
            assert len(series) == 1

            series = series[0]
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
