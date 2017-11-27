#!/usr/bin/env python
# -*- coding: utf-8 -*-

################################################################################
#
# caos-collector - CAOS collector
#
# Copyright © 2017 INFN - Istituto Nazionale di Fisica Nucleare (Italy)
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

from job import Job
from caos_collector import cfg
from caos_collector import metrics
from caos_collector import openstack
from caos_collector import tsdb
from caos_collector import utils
from caos_collector.pollsters import CPUTimePollster
from caos_collector.pollsters import WallClockTimePollster
from caos_collector.pollsters import WallClockTimeOcataPollster


class VMUsageJob(Job):
    """The VM usage job"""

    def __init__(self, *args, **kwargs):
        super(VMUsageJob, self).__init__(
            name=__name__, *args, **kwargs)

    @staticmethod
    def setup_parser(parser):
        parser.add_argument(
            '-d', '--domain',
            dest='domain_id', metavar='ID',
            nargs='?',
            default=None,
            help='Limit by domain id')

        parser.add_argument(
            '-p', '--project',
            dest='project_id', metavar='ID',
            nargs='?',
            default=None,
            help='Limit by project id')

        parser.add_argument(
            '-s', '--start',
            dest='start', metavar='TS',
            nargs='?',
            default=utils.format_date(datetime.datetime.utcnow()),
            help='Perform collection since TIMESTAMP (default to now)')

        parser.add_argument(
            '-e', '--end',
            dest='end', metavar='TS',
            nargs='?',
            default=utils.format_date(datetime.datetime.utcnow()),
            help='Perform collection up to TIMESTAMP (default to now)')

        parser.add_argument(
            '-P', '--period',
            dest='period', metavar='PERIOD',
            nargs='?',
            type=int,
            default=3600,
            help='Limit by period')

        parser.add_argument(
            '-m', '--misfire',
            dest='misfire', metavar='SECONDS',
            nargs='?',
            type=int,
            default=0,
            help='Misfire grace time')

        parser.add_argument(
            '-o', '--overwrite',
            dest='overwrite',
            action='store_const',
            const=True,
            default=False,
            help='Overwrite samples')

        parser.add_argument(
            '-C', '--current',
            dest='current',
            action='store_const',
            const=True,
            default=False,
            help='Only update current period')

    def _run(self, args):
        domain_id = args.domain_id
        project_id = args.project_id
        period = args.period
        start = utils.parse_date(args.start)
        if start > datetime.datetime.utcnow():
            self.logger.warn("Start date is in the future. Resetting to NOW.")
            start = datetime.datetime.utcnow()

        end = utils.parse_date(args.end)
        if end < start:
            self.logger.warn(
                "End date is before start date. Resetting to start date.")
            end = start

        overwrite = args.overwrite
        if args.current:
            overwrite = True

        if project_id:
            keystone_projects = openstack.project(project_id=project_id)
        else:
            # get projects from keystone
            keystone_projects = openstack.projects(domain_id=domain_id)

        for project_id, project_data in keystone_projects.items():
            project_name = project_data['name']

            self.logger.info("Checking VM usages for project {id} ({name})"
                             .format(id=project_id, name=project_name))

            grid = self._grid(start=start, end=end, period=period,
                              current=args.current, misfire=False)
            for ts in grid:
                self.check_nova_usage(
                    project_id=project_id,
                    period=period,
                    end=ts,
                    start=ts - datetime.timedelta(seconds=period),
                    overwrite=overwrite)

            last_timestamp = tsdb.last_timestamp(
                tags=[{'key': cfg.CAOS_PROJECT_TAG_KEY,
                       'value': project_id}],
                metric_name=metrics.METRIC_VM_CPU_TIME_USAGE,
                period=period)

            grid = self._grid(
                start=start,
                end=end,
                period=period,
                current=args.current,
                misfire=args.misfire,
                last_timestamp=last_timestamp)

            for ts in grid:
                self.check_cpu_time(
                    project_id=project_id,
                    period=period,
                    end=ts,
                    start=ts - datetime.timedelta(seconds=period),
                    overwrite=overwrite)

            last_timestamp = tsdb.last_timestamp(
                tags=[{'key': cfg.CAOS_PROJECT_TAG_KEY,
                       'value': project_id}],
                metric_name=metrics.METRIC_VM_WALLCLOCK_TIME_USAGE,
                period=period)

            grid = self._grid(
                start=start,
                end=end,
                period=period,
                current=args.current,
                misfire=args.misfire,
                last_timestamp=last_timestamp)

            for ts in grid:
                self.check_wallckock_time(
                    project_id=project_id,
                    period=period,
                    end=ts,
                    start=ts - datetime.timedelta(seconds=period),
                    overwrite=overwrite)

            self.logger.info("VM usages updated")

    def _grid(self, start, end, period, current, misfire,
              last_timestamp=utils.EPOCH):
        if current:
            now = datetime.datetime.utcnow()
            end = now + datetime.timedelta(seconds=period)
            return utils.timeline(period=period, start=now, end=end)

        # we respect a misfire grace time greater then the period
        if misfire and misfire < period:
            misfire = 0

        if not misfire:
            start = start - datetime.timedelta(seconds=period)
            return utils.timeline(period=period, start=start, end=end)

        # If we have at least one period between now (end) and
        # last_timestamp, then we collect (also respecting the misfire
        # grace time).
        if last_timestamp < end - datetime.timedelta(seconds=misfire):
            self.logger.info(
                "Dropping history collection due to misfire grace time={m}"
                .format(m=misfire))

            last_timestamp = end - datetime.timedelta(seconds=misfire)

        grid = utils.timeline(period=period, start=last_timestamp, end=end)
        if len(grid) == 0:
            # the series is already update
            self.logger.info("Series is uptodate")

        return grid

    def check_nova_usage(self, project_id, period, start, end, overwrite):
        self.logger.info(
            "Checking nova usages for project {id} from {s} to {e}"
            .format(id=project_id, name=project_id, s=start, e=end))

        usage = openstack.nova_usage(start=start, end=end,
                                     project_id=project_id)

        tag = {
            'key': cfg.CAOS_PROJECT_TAG_KEY,
            'value': project_id
        }

        if 'total_vcpus_usage' in usage:
            tsdb.create_sample(metric_name=metrics.METRIC_VM_VCPUS_USAGE,
                               period=period,
                               tags=[tag],
                               timestamp=end,
                               value=usage['total_vcpus_usage'] * utils.u1_hour,
                               overwrite=overwrite)

        if 'total_local_gb_usage' in usage:
            tsdb.create_sample(
                metric_name=metrics.METRIC_VM_DISK_USAGE,
                period=period,
                tags=[tag],
                timestamp=end,
                value=usage['total_local_gb_usage'] * utils.u1_G * utils.u1_hour,  # noqa: E501
                overwrite=overwrite)

        if 'total_memory_mb_usage' in usage:
            tsdb.create_sample(
                metric_name=metrics.METRIC_VM_MEMORY_USAGE,
                period=period,
                tags=[tag],
                timestamp=end,
                value=usage['total_memory_mb_usage'] * utils.u1_M * utils.u1_hour,  # noqa: E501
                overwrite=overwrite)

        instances = []
        deleted_instances = []

        # Attribute may not exist if there are no instances
        if 'server_usages' in usage:
            for server_usage in usage['server_usages']:
                if server_usage['ended_at']:
                    deleted_instances.append(server_usage)
                else:
                    instances.append(server_usage)
        tsdb.create_sample(metric_name=metrics.METRIC_VM_COUNT_ACTIVE,
                           period=period,
                           tags=[tag],
                           timestamp=end,
                           value=len(instances),
                           overwrite=overwrite)

        tsdb.create_sample(metric_name=metrics.METRIC_VM_COUNT_DELETED,
                           period=period,
                           tags=[tag],
                           timestamp=end,
                           value=len(deleted_instances),
                           overwrite=overwrite)

    def check_cpu_time(self, project_id, period, start, end, overwrite):
        self.logger.info(
            "Checking cpu time for project {id} from {s} to {e}"
            .format(id=project_id, name=project_id, s=start, e=end))

        pollster = CPUTimePollster(project_id=project_id,
                                   period=period,
                                   start=start,
                                   end=end)
        sample = pollster.measure()
        if sample is None:
            self.logger.info("Skipping null cpu time sample")
            return

        tag = {
            'key': cfg.CAOS_PROJECT_TAG_KEY,
            'value': project_id
        }

        tsdb.create_sample(metric_name=metrics.METRIC_VM_CPU_TIME_USAGE,
                           period=period,
                           tags=[tag],
                           timestamp=end,
                           overwrite=overwrite,
                           value=sample)

    def check_wallckock_time(self, project_id, period, start, end, overwrite):
        self.logger.info(
            "Checking wallclocktime time for project {id} from {s} to {e}"
            .format(id=project_id, name=project_id, s=start, e=end))

        if cfg.OPENSTACK_VERSION < 'ocata':
            pollster_class = WallClockTimePollster
        else:
            pollster_class = WallClockTimeOcataPollster

        pollster = pollster_class(project_id=project_id,
                                  period=period,
                                  start=start,
                                  end=end)

        sample = pollster.measure()
        if sample is None:
            self.logger.info("Skipping null wallclocktime time sample")
            return

        tag = {
            'key': cfg.CAOS_PROJECT_TAG_KEY,
            'value': project_id
        }

        tsdb.create_sample(metric_name=metrics.METRIC_VM_WALLCLOCK_TIME_USAGE,
                           period=period,
                           tags=[tag],
                           timestamp=end,
                           overwrite=overwrite,
                           value=sample)
