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
import signal
import StringIO

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor

import cfg
import log
import utils


logger = log.get_logger(__name__)


_scheduler = None


def initialize():
    logger.info("Initializing scheduler...")
    global _scheduler

    log.setup_apscheduler_logger()
    _scheduler = BlockingScheduler(
        timezone="utc",
        executors={
            'default': ThreadPoolExecutor(1)})

    # the special alive job
    report_alive_period = cfg.SCHEDULER_REPORT_ALIVE_PERIOD
    logger.info("Registering job REPORT_ALIVE running every %ds." % report_alive_period)

    add_job(func=report_alive_job,

            # trigger that determines when func is called
            trigger='interval',
            seconds=report_alive_period,

            name="report_alive",
            kwargs={
                "scheduler": _scheduler,
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


def report_alive_job(scheduler):
    logger.info("Scheduler is alive")

    output = StringIO.StringIO()
    scheduler.print_jobs(out=output)
    logger.info(output.getvalue())
    output.close()


def add_job(*args, **kwargs):
    _scheduler.add_job(*args, **kwargs)


def main_loop():
    def sigterm_handler(_signo, _stack_frame):
        # Raises SystemExit(0):
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    # this is blocking
    try:
        _scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info('Got SIGTERM! Terminating...')
        _scheduler.shutdown(wait=False)
