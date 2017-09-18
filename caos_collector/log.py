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

import logging
from logging.handlers import TimedRotatingFileHandler

from . import __package_name__
import cfg


_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def get_root_logger():
    return logging.getLogger(__package_name__)


def initialize():
    logger = get_root_logger()
    logger.info("Logger setup.")


def get_logger(name):
    return get_root_logger().getChild(name)


def _setup_logger(logger):
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(_formatter)
    logger.addHandler(ch)

    ch = TimedRotatingFileHandler(cfg.LOGGER_LOG_FILE_PATH,
                                  when='midnight',
                                  backupCount=cfg.LOGGER_ROTATE_KEEP_COUNT,
                                  utc=True)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(_formatter)
    logger.addHandler(ch)

    ch = TimedRotatingFileHandler(cfg.LOGGER_ERROR_FILE_PATH,
                                  when='midnight',
                                  backupCount=cfg.LOGGER_ROTATE_KEEP_COUNT,
                                  utc=True)
    ch.setLevel(logging.ERROR)
    ch.setFormatter(_formatter)
    logger.addHandler(ch)


def setup_root_logger():
    logger = get_root_logger()
    _setup_logger(logger)


def setup_apscheduler_logger():
    logger = logging.getLogger('apscheduler')
    _setup_logger(logger)
