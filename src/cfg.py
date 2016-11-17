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

import ConfigParser
import os
from pprint import pprint
import sys


import log
logger = log.get_logger(__name__)

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
KEYSTONE_PROJECT_NAME = None
KEYSTONE_DOMAIN_ID = None
KEYSTONE_DOMAIN_NAME = None
KEYSTONE_USER_DOMAIN_ID = None
KEYSTONE_USER_DOMAIN_NAME = None
KEYSTONE_PROJECT_DOMAIN_ID = None
KEYSTONE_PROJECT_DOMAIN_NAME = None
KEYSTONE_CACERT = None
KEYSTONE_API_VERSION = None

SCHEDULER_REPORT_ALIVE_PERIOD = None

COLLECTOR_MISFIRE_GRACE_TIME = None

CAOS_API_URL = None
CAOS_API_USERNAME = None
CAOS_API_PASSWORD = None

CEILOMETER_MONGODB = None
CEILOMETER_MONGODB_CONNECTION_TIMEOUT = None
CEILOMETER_POLLING_PERIOD = None

LOGGER_FILE = None
LOGGER_ROTATE_BYTES = None
LOGGER_ROTATE_COUNT = None

# defaults
DEFAULT_CEILOMETER_MONGODB_CONNECTION_TIMEOUT = 1
DEFAULT_KEYSTONE_API_VERSION = "v3"
DEFAULT_LOGGER_FILE = "/var/log/caos/collector.log"
DEFAULT_LOGGER_ROTATE_BYTES = (1048576*5)
DEFAULT_LOGGER_ROTATE_COUNT = 30

def _parse_cfg():
    _assign('METRICS', _get_metrics())
    _assign('PERIODS', _get_periods())
    _assign('SERIES', _get_series())

    _assign('LOGGER_FILE',
            _get("logger", "file", "", DEFAULT_LOGGER_FILE))

    _assign('LOGGER_ROTATE_BYTES',
            _get("logger", "rotate_bytes", "int", DEFAULT_LOGGER_ROTATE_BYTES))

    _assign('LOGGER_ROTATE_COUNT',
            _get("logger", "rotate_count", "int", DEFAULT_LOGGER_ROTATE_COUNT))

    _assign('KEYSTONE_USERNAME', _get("keystone", "username"))
    _assign('KEYSTONE_PASSWORD', _get("keystone", "password"))
    _assign('KEYSTONE_AUTH_URL', _get("keystone", "auth_url"))
    _assign('KEYSTONE_PROJECT_ID', _get("keystone", "project_id", required=False))
    _assign('KEYSTONE_PROJECT_NAME', _get("keystone", "project_name", required=False))
    _assign('KEYSTONE_DOMAIN_ID', _get("keystone", "domain_id", required=False))
    _assign('KEYSTONE_DOMAIN_NAME', _get("keystone", "domain_name", required=False))
    _assign('KEYSTONE_USER_DOMAIN_ID', _get("keystone", "user_domain_id", required=False))
    _assign('KEYSTONE_USER_DOMAIN_NAME', _get("keystone", "user_domain_name", required=False))
    _assign('KEYSTONE_PROJECT_DOMAIN_ID', _get("keystone", "project_domain_id", required=False))
    _assign('KEYSTONE_PROJECT_DOMAIN_NAME', _get("keystone", "project_domain_name", required=False))
    _assign('KEYSTONE_CACERT', _get("keystone", "cacert"))
    _assign('KEYSTONE_API_VERSION',
            _get("keystone", "identity_api_version", "", DEFAULT_KEYSTONE_API_VERSION))

    # [scheduler]
    _assign('SCHEDULER_REPORT_ALIVE_PERIOD',
            _get("scheduler", "report_alive_period", 'int'))

    # [collector]
    _assign('COLLECTOR_MISFIRE_GRACE_TIME',
            _get("collector", "misfire_grace_time", "int"))

    # [caos-api]
    _assign('CAOS_API_URL', _get('caos-api', 'api_url'))
    _assign('CAOS_API_USERNAME', _get('caos-api', 'username'))
    _assign('CAOS_API_PASSWORD', _get('caos-api', 'password'))

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


def _get(section, option=None, type='str', default=None, required=True):
    if not _config.has_section(section) and section != "DEFAULT" and not default and required:
        raise RuntimeError("No [%s] section in config file." % section)

    if option and not _config.has_option(section, option):
        if required and not default:
            raise RuntimeError("No [%s]/%s option in config file." % (section, option))
        return default

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
