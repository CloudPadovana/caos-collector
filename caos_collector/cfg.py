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

import yaml
import os
from pprint import pprint
import sys


import log
import utils


logger = log.get_logger(__name__)

# parsed config file
_config = None

# dict for custom cfg
CFG = {}

# options
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

SCHEDULERS = None

CAOS_TSDB_API_URL = None
CAOS_TSDB_API_USERNAME = None
CAOS_TSDB_API_PASSWORD = None

CEILOMETER_MONGODB = None
CEILOMETER_MONGODB_CONNECTION_TIMEOUT = None
CEILOMETER_POLLING_PERIOD = None

LOGGER_ROTATE_KEEP_COUNT = None
LOGGER_LOG_PATH = None
LOGGER_ERROR_LOG_PATH = None

OPENSTACK_NOVA_API_VERSION = None

# defaults
DEFAULT_CEILOMETER_MONGODB_CONNECTION_TIMEOUT = 1
DEFAULT_KEYSTONE_API_VERSION = "v3"
DEFAULT_OPENSTACK_NOVA_API_VERSION = "2"
DEFAULT_LOGGER_ROTATE_KEEP_COUNT = 30
DEFAULT_LOGGER_LOG_PATH = "/var/log/caos/collector.log"
DEFAULT_LOGGER_ERROR_LOG_PATH = "/var/log/caos/collector.error.log"

# misc
CAOS_DOMAIN_TAG_KEY = 'domain'
CAOS_HYPERVISOR_TAG_KEY = 'hypervisor'
CAOS_PROJECT_TAG_KEY = 'project'


def _parse_cfg():
    _assign('SCHEDULERS', _get_schedulers())

    _assign('LOGGER_ROTATE_KEEP_COUNT',
            _get_int("logger.rotate_keep_count",
                     default=DEFAULT_LOGGER_ROTATE_KEEP_COUNT))
    _assign('LOGGER_LOG_PATH',
            _get_str("logger.log.path", default=DEFAULT_LOGGER_LOG_PATH))
    _assign('LOGGER_ERROR_LOG_PATH',
            _get_str("logger.error_log.path", default=DEFAULT_LOGGER_ERROR_LOG_PATH))

    _assign('KEYSTONE_USERNAME', _get_str("keystone.username"))
    _assign('KEYSTONE_PASSWORD', _get_str("keystone.password"))
    _assign('KEYSTONE_AUTH_URL', _get_str("keystone.auth_url"))
    _assign('KEYSTONE_PROJECT_ID', _get_str("keystone.project_id",
                                            required=False))
    _assign('KEYSTONE_PROJECT_NAME', _get_str("keystone.project_name",
                                              required=False))
    _assign('KEYSTONE_DOMAIN_ID', _get_str("keystone.domain_id",
                                           required=False))
    _assign('KEYSTONE_DOMAIN_NAME', _get_str("keystone.domain_name",
                                             required=False))
    _assign('KEYSTONE_USER_DOMAIN_ID', _get_str("keystone.user_domain_id",
                                                required=False))
    _assign('KEYSTONE_USER_DOMAIN_NAME', _get_str("keystone.user_domain_name",
                                                  required=False))
    _assign('KEYSTONE_PROJECT_DOMAIN_ID', _get_str("keystone.project_domain_id",
                                                   required=False))
    _assign('KEYSTONE_PROJECT_DOMAIN_NAME',
            _get_str("keystone.project_domain_name",
                     required=False))
    _assign('KEYSTONE_CACERT', _get_str("keystone.cacert"))
    _assign('KEYSTONE_API_VERSION',
            _get_str("keystone.identity_api_version",
                     default=DEFAULT_KEYSTONE_API_VERSION))

    # [openstack]
    _assign('OPENSTACK_NOVA_API_VERSION',
            _get_str("openstack.nova_api_version",
                     default=DEFAULT_OPENSTACK_NOVA_API_VERSION))

    # [caos-tsdb]
    _assign('CAOS_TSDB_API_URL', _get_str('caos-tsdb.api_url'))
    _assign('CAOS_TSDB_API_USERNAME', _get_str('caos-tsdb.username'))
    _assign('CAOS_TSDB_API_PASSWORD', _get_str('caos-tsdb.password'))

    # [ceilometer]
    _assign('CEILOMETER_MONGODB', _get_str('ceilometer.mongodb'))
    _assign('CEILOMETER_MONGODB_CONNECTION_TIMEOUT',
            _get_int('ceilometer.mongodb_connection_timeout',
                     default=DEFAULT_CEILOMETER_MONGODB_CONNECTION_TIMEOUT))
    _assign('CEILOMETER_POLLING_PERIOD', _get_int("ceilometer.polling_period"))


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

    if not os.path.exists(cfg_file) or not os.path.isfile(cfg_file):
        raise RuntimeError("cfg file '%s' doesn't exists" % cfg_file)

    with open(cfg_file, 'r') as ymlfile:
        _config = yaml.safe_load(ymlfile)

    _parse_cfg()


def _get(name, default=None, required=True, check_type=None):
    value = utils.deep_get(_config, name)

    if required and not value:
        if default:
            return default
        raise RuntimeError("No `{name}` in config file.".format(name=name))

    if not check_type or not value:
        return value

    # check type
    if not type(value) is check_type:
        raise RuntimeError("Option `{name}` must be a `{type}`"
                           .format(name=name, type=check_type.__name__))

    return value


def _get_str(*args, **kwargs):
    return _get(*args, check_type=str, **kwargs)


def _get_int(*args, **kwargs):
    value = _get(*args, check_type=int, **kwargs)
    if value:
        return int(value)
    return None


def _get_int_or_str(*args, **kwargs):
    try:
        value = _get_int(*args, **kwargs)
    except:
        value = _get_str(*args, **kwargs)

    return value


def _get_scheduler(name):
    OPTIONS = [
        'jobs',
        'misfire_grace_time',
    ]
    CRON_OPTIONS = [
        'day',
        'hour',
        'minute',
        'second',
    ]

    for k in _get("schedulers.{name}".format(name=name)):
        if k not in OPTIONS + CRON_OPTIONS:
            raise RuntimeError("Unknown option `{option}` in `{section}`"
                               .format(option=k,
                                       section="schedulers.{name}".format(
                                           name=name)))

    ret = {}

    cron_kwargs = {}
    for opt in CRON_OPTIONS:
        value = _get_int_or_str("schedulers.{name}.{opt}"
                                .format(name=name, opt=opt), required=False)
        if value:
            cron_kwargs[opt] = value

    cron_kwargs['misfire_grace_time'] = _get_int(
        "schedulers.{name}.misfire_grace_time".format(name=name))

    ret['cron_kwargs'] = cron_kwargs
    ret['jobs'] = _get("schedulers.{name}.jobs".format(name=name))

    return ret


def _get_schedulers():
    ret = {}

    schedulers = _get('schedulers', required=True)
    for name in schedulers:
        ret[name] = _get_scheduler(name)

    return ret
