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

import argparse
from functools import partial
import shlex
import sys

from . import __version__, __description__
import cfg
import log
import scheduler

from jobs.domains_metadata_job import DomainsMetadataJob
from jobs.hypervisors_metadata_job import HypervisorsMetadataJob
from jobs.hypervisors_state_job import HypervisorsStateJob
from jobs.projects_metadata_job import ProjectsMetadataJob
from jobs.projects_quotas_job import ProjectsQuotasJob
from jobs.report_alive_job import ReportAliveJob
from jobs.vm_usage_job import VMUsageJob


log.initialize()
logger = log.get_logger(__name__)

DEFAULT_CFG_FILE = '/etc/caos/collector.conf.yaml'

_JOBS = {
    'report_alive': ReportAliveJob,

    'domains_metadata': DomainsMetadataJob,
    'projects_metadata': ProjectsMetadataJob,
    'hypervisors_metadata': HypervisorsMetadataJob,

    'projects_quotas': ProjectsQuotasJob,
    'vm_usage': VMUsageJob,
    'hypervisors_state': HypervisorsStateJob,
}

for job_name, job_class in _JOBS.items():
    if not job_class.__doc__:
        raise NotImplementedError("Job `{job}` miss __doc__"
                                  .format(job=job_class))


def setup_parser():
    parser = argparse.ArgumentParser(description=__description__,
                                     add_help=True)

    parser.add_argument('-v', '--version', action='version',
                        version='%(prog)s {version}'.format(
                            version=__version__))

    parser.add_argument('-c', '--config',
                        dest='cfg_file', metavar='FILE',
                        default=DEFAULT_CFG_FILE,
                        help='configuration file')

    subparsers = parser.add_subparsers(dest="job", help='job')
    subparsers.add_parser('daemon', help='daemon mode')
    subparsers.add_parser('run', help='run scheduler')

    subparsers.required = False

    for job_name, job_class in _JOBS.items():
        subparser = subparsers.add_parser(job_name,
                                          help=job_class.__doc__)
        job_class.setup_parser(subparser)

    return parser


def get_job_instance(name):
    job_class = _JOBS[name]
    return job_class()


def run_scheduler(scheduler_name, parser):
    if scheduler_name not in cfg.SCHEDULERS:
        logger.error("Scheduler '{name}' not found in configuration file"
                     .format(name=scheduler_name))
        sys.exit(1)

    scheduler_cfg = cfg.SCHEDULERS[scheduler_name]
    jobs = scheduler_cfg['jobs']
    for cmdline in jobs:
        args = parser.parse_args(shlex.split(cmdline))
        job_name = args.job
        job_instance = get_job_instance(job_name)

        func = partial(job_instance.run_job, args)
        logger.info("Running job {cmd_line} for scheduler {name}"
                    .format(name=scheduler_name, cmd_line=cmdline))
        func()
        logger.info("Finished job {cmd_line} for scheduler {name}"
                    .format(name=scheduler_name, cmd_line=cmdline))


def setup_scheduler(parser):
    scheduler.initialize()

    schedulers = cfg.SCHEDULERS
    for name, scheduler_cfg in schedulers.items():
        jobs = scheduler_cfg['jobs']
        for cmdline in jobs:
            args = parser.parse_args(shlex.split(cmdline))
            job_name = args.job
            job_instance = get_job_instance(job_name)

            func = partial(job_instance.run_job, args)

            cron_kwargs = scheduler_cfg['cron_kwargs']

            scheduler.add_job(func=func,

                              # trigger that determines when func is called
                              trigger='cron',
                              name="{name}__{job_name}".format(
                                  name=name, job_name=job_name),

                              # args given to the job
                              kwargs=None,

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
                              #
                              # next_run_time=None,

                              **cron_kwargs)

            logger.info("Registered job {cmd_line} for scheduler {name}"
                        .format(name=name, cmd_line=cmdline))


def main():
    parser = setup_parser()
    args = parser.parse_args()
    cfg_file = args.cfg_file
    cfg.read(cfg_file)
    cfg.dump()
    log.setup_root_logger()

    job_name = args.job
    if job_name == 'daemon':
        setup_scheduler(parser)

        # this is blocking!!!
        scheduler.main_loop()

    if job_name == 'run':
        run_scheduler(job_name, parser)
        sys.exit(0)

    if job_name not in _JOBS:
        logger.error("Unknown job '%s'", job_name)
        sys.exit(1)

    job_instance = get_job_instance(job_name)
    job_instance.run_job(args)
