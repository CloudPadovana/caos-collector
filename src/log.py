#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: log.py
# Created: 2016-07-01T12:30:34+0200
# Time-stamp: <2016-07-29T15:04:20cest>
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

import logging
import logging.handlers
import os

_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')


def get_logger():
    return logging.getLogger("collector")


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
    log_file = cfg.COLLECTOR_LOG_FILE
    log_dir = os.path.dirname(log_file)

    if not os.path.isdir(log_dir):
        logger.info("Creating log dir %s", log_dir)
        os.mkdir(log_dir)


    ch = logging.handlers.RotatingFileHandler(cfg.COLLECTOR_LOG_FILE,
                                              maxBytes=cfg.COLLECTOR_LOG_ROTATE_BYTES,
                                              backupCount=cfg.COLLECTOR_LOG_ROTATE_COUNT)
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(_formatter)

    logger.addHandler(ch)

    logger = logging.getLogger('apscheduler')
    logger.addHandler(ch)

    logger.info("Setup log to file %s", cfg.COLLECTOR_LOG_FILE)
