#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: cfg.py
# Created: 2016-07-19T15:03:22+0200
# Time-stamp: <2016-07-21T17:47:54cest>
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

import ConfigParser
import os

import log
logger = log.get_logger()


_config = None


def read(cfg_file):
    logger.info("Reading configuration file: %s." % cfg_file)

    global _config
    if _config:
        raise RuntimeError("cfg file already parsed")

    fname = None
    if os.path.exists(cfg_file) and os.path.isfile(cfg_file):
        fname = cfg_file

    if not fname:
        raise RuntimeError("cfg file '%s' doesn't exists", cfg_file)

    _config = ConfigParser.RawConfigParser()
    _config.read(fname)


def get(section, option=None, type='str', default=None):
    if not _config.has_section(section) and section != "DEFAULT" and not default:
        raise RuntimeError("No [%s] section in config file." % section)

    if option and not _config.has_option(section, option):
        if default:
            return default
        raise RuntimeError("No [%s]/%s option in config file." % (section, option))

    if not option:
        return _config.options(section)

    if type == 'str':
        fun = getattr(_config, "get")
    else:
        fun = getattr(_config, "get%s" % type)

    return fun(section, option)


def get_os_envs(opts):
    return dict((opt, get("keystone", opt)) for opt in opts)


def get_metrics():
    ret = {}
    for s in _config.sections():
        PREFIX = 'metric/'
        if s.startswith(PREFIX):
            _, name = s.split('/')
            ret[name] = {
                "type": get(s, 'type')
            }
    return ret


def get_periods():
    periods = get('periods')
    return dict((p, get('periods', p, 'int')) for p in periods)


def get_series():
    periods = get_periods()
    metrics = get_metrics()

    ret = []
    for s in _config.sections():
        PREFIX = 'series/'
        if s.startswith(PREFIX):
            _, metric_name, period = s.split('/')
            ret.append({
                "metric_name": metric_name,
                "period": periods[period],
                "ttl": get(s, 'ttl', 'int')})
    return ret
