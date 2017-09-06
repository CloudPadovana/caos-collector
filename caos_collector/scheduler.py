#!/usr/bin/env python
# -*- coding: utf-8 -*-

################################################################################
#
# caos-collector - CAOS collector
#
# Copyright © 2016, 2017 INFN - Istituto Nazionale di Fisica Nucleare (Italy)
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

import signal
import StringIO
import sys

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_ERROR

import log


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


def report_alive():
    logger.info("Scheduler is alive")

    output = StringIO.StringIO()
    _scheduler.print_jobs(out=output)
    logger.info(output.getvalue())
    output.close()


def add_job(*args, **kwargs):
    _scheduler.add_job(*args, **kwargs)


def error_listener(event):
    if event.exception:
        logger.error("Job ERROR: {exception} -- {trace}".format(
            exception=event.exception, trace=event.traceback))


def main_loop():
    def sigterm_handler(_signo, _stack_frame):
        # Raises SystemExit(0):
        sys.exit(0)

    signal.signal(signal.SIGTERM, sigterm_handler)

    # log errors
    _scheduler.add_listener(error_listener, EVENT_JOB_ERROR)

    # this is blocking
    try:
        _scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info('Got SIGTERM! Terminating...')
        _scheduler.shutdown(wait=False)
