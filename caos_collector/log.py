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

import logging
import logging.handlers
import os

_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_LOGGER_ROOT_NAME = "caos-collector"

def get_logger(name=None):
    root_logger = logging.getLogger(_LOGGER_ROOT_NAME)
    if name:
        return root_logger.getChild(name)
    return root_logger


def setup_logger():
    logger = get_logger()
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(_formatter)
    logger.addHandler(ch)


def setup_apscheduler_logger():
    logger = logging.getLogger('apscheduler')
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(_formatter)
    logger.addHandler(ch)


def setup_file_handlers():
    logger = get_logger()

    import cfg
    log_file = cfg.LOGGER_FILE
    log_dir = os.path.dirname(log_file)

    if not os.path.isdir(log_dir):
        logger.info("Creating log dir %s", log_dir)
        os.mkdir(log_dir)


    ch = logging.handlers.RotatingFileHandler(cfg.LOGGER_FILE,
                                              maxBytes=cfg.LOGGER_ROTATE_BYTES,
                                              backupCount=cfg.LOGGER_ROTATE_COUNT)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(_formatter)

    logger.addHandler(ch)

    logger = logging.getLogger('apscheduler')
    logger.addHandler(ch)

    logger.info("Setup log to file %s", cfg.LOGGER_FILE)