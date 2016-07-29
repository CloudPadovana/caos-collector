#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: cfg.py
# Created: 2016-07-19T15:03:22+0200
# Time-stamp: <2016-07-29T14:51:19cest>
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
from pprint import pprint
import sys


import log
logger = log.get_logger()

# parsed config file
_config = None

# dict for custom cfg
CFG = {}

# options
METRICS = None
PERIODS = None
SERIES = None

KEYSTONE_USERNAME = None
KEYSTONE_PASSWORD = None
KEYSTONE_AUTH_URL = None
KEYSTONE_PROJECT_ID = None
KEYSTONE_USER_DOMAIN_ID = None
KEYSTONE_CACERT = None

SCHEDULER_REPORT_ALIVE_PERIOD = None

COLLECTOR_MISFIRE_GRACE_TIME = None
COLLECTOR_LOG_FILE = None
COLLECTOR_LOG_ROTATE_BYTES = None
COLLECTOR_LOG_ROTATE_COUNT = None

CAOS_API_URL = None

CEILOMETER_MONGODB = None
CEILOMETER_MONGODB_CONNECTION_TIMEOUT = None
CEILOMETER_POLLING_PERIOD = None

# defaults
DEFAULT_CEILOMETER_MONGODB_CONNECTION_TIMEOUT = 1
DEFAULT_COLLECTOR_LOG_FILE = "/var/log/caos/collector.log"
DEFAULT_COLLECTOR_LOG_ROTATE_BYTES = (1048576*5)
DEFAULT_COLLECTOR_LOG_ROTATE_COUNT = 30

def _parse_cfg():
    _assign('METRICS', _get_metrics())
    _assign('PERIODS', _get_periods())
    _assign('SERIES', _get_series())

    _assign('KEYSTONE_USERNAME', _get("keystone", "username"))
    _assign('KEYSTONE_PASSWORD', _get("keystone", "password"))
    _assign('KEYSTONE_AUTH_URL', _get("keystone", "auth_url"))
    _assign('KEYSTONE_PROJECT_ID', _get("keystone", "project_id"))
    _assign('KEYSTONE_USER_DOMAIN_ID', _get("keystone", "user_domain_id"))
    _assign('KEYSTONE_CACERT', _get("keystone", "cacert"))

    # [scheduler]
    _assign('SCHEDULER_REPORT_ALIVE_PERIOD',
            _get("scheduler", "report_alive_period", 'int'))

    # [collector]
    _assign('COLLECTOR_MISFIRE_GRACE_TIME',
            _get("collector", "misfire_grace_time", "int"))

    _assign('COLLECTOR_LOG_FILE',
            _get("collector", "log_file", "", DEFAULT_COLLECTOR_LOG_FILE))

    _assign('COLLECTOR_LOG_ROTATE_BYTES',
            _get("collector", "log_rotate_bytes", "int", DEFAULT_COLLECTOR_LOG_ROTATE_BYTES))

    _assign('COLLECTOR_LOG_ROTATE_COUNT',
            _get("collector", "log_rotate_count", "int", DEFAULT_COLLECTOR_LOG_ROTATE_COUNT))

    # [caos-api]
    _assign('CAOS_API_URL', _get('caos-api', 'api_url'))

    # [ceilometer]
    _assign('CEILOMETER_MONGODB', _get('ceilometer', 'mongodb'))
    _assign('CEILOMETER_MONGODB_CONNECTION_TIMEOUT',
            _get('ceilometer', 'mongodb_connection_timeout',
                 'int', DEFAULT_CEILOMETER_MONGODB_CONNECTION_TIMEOUT))
    _assign('CEILOMETER_POLLING_PERIOD', _get("ceilometer", "polling_period", "int"))

def dump():
    pprint({'CFG': CFG})


def _assign(name, value):
    CFG[name] = value

    module = sys.modules[__name__]

    if not hasattr(module, name):
        raise Exception("cfg option %s not defined" % name)

    if getattr(module, name) is not None:
        raise Exception("redefining cfg option %s" % name)

    setattr(module, name, value)
    return value


def read(cfg_file):
    logger.info("Reading configuration file: %s." % cfg_file)

    global _config
    if _config:
        raise RuntimeError("cfg file already parsed")

    fname = None
    if os.path.exists(cfg_file) and os.path.isfile(cfg_file):
        fname = cfg_file

    if not fname:
        raise RuntimeError("cfg file '%s' doesn't exists" % cfg_file)

    _config = ConfigParser.RawConfigParser()
    _config.read(fname)

    _parse_cfg()


def _get(section, option=None, type='str', default=None):
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


# FIXME: in the future the following structs should be queried from caos-api
def _get_metrics():
    ret = {}
    for s in _config.sections():
        PREFIX = 'metric/'
        if s.startswith(PREFIX):
            _, name = s.split('/')
            ret[name] = {
                "type": _get(s, 'type')
            }
    return ret


def _get_periods():
    periods = _get('periods')
    return dict((p, _get('periods', p, 'int')) for p in periods)


def _get_series():
    periods = _get_periods()
    metrics = _get_metrics()

    ret = []
    for s in _config.sections():
        PREFIX = 'series/'
        if s.startswith(PREFIX):
            _, metric_name, period = s.split('/')
            ret.append({
                "metric_name": metric_name,
                "period": periods[period],
                "ttl": _get(s, 'ttl', 'int')})
    return ret
