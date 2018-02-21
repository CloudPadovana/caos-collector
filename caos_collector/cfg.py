#!/usr/bin/env python
# -*- coding: utf-8 -*-

################################################################################
#
# caos-collector - CAOS collector
#
# Copyright © 2016, 2017, 2018 INFN - Istituto Nazionale di Fisica Nucleare (Italy)
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

CEILOMETER_BACKEND = None
CEILOMETER_MONGODB = None
CEILOMETER_MONGODB_CONNECTION_TIMEOUT = None
CEILOMETER_POLLING_PERIOD = None
CEILOMETER_GNOCCHI_POLICY_GRANULARITY = None

LOGGER_ROTATE_KEEP_COUNT = None
LOGGER_LOG_FILE_PATH = None
LOGGER_ERROR_FILE_PATH = None

OPENSTACK_NOVA_API_VERSION = None

OPENSTACK_PLACEMENT_API_VERSION = None
OPENSTACK_PLACEMENT_ENDPOINT = None

OPENSTACK_VERSION = None

# defaults
DEFAULT_CEILOMETER_BACKEND = "mongodb"
DEFAULT_CEILOMETER_MONGODB_CONNECTION_TIMEOUT = 1
DEFAULT_CEILOMETER_GNOCCHI_POLICY_GRANULARITY = 300
DEFAULT_KEYSTONE_API_VERSION = "v3"
DEFAULT_OPENSTACK_NOVA_API_VERSION = "2"
DEFAULT_OPENSTACK_PLACEMENT_API_VERSION = "1.4"
DEFAULT_OPENSTACK_PLACEMENT_ENDPOINT = None
DEFAULT_OPENSTACK_VERSION = 'newton'
DEFAULT_LOGGER_ROTATE_KEEP_COUNT = 30
DEFAULT_LOGGER_LOG_FILE_PATH = "/var/log/caos/collector.log"
DEFAULT_LOGGER_ERROR_FILE_PATH = "/var/log/caos/collector.error.log"

# misc
CAOS_DOMAIN_TAG_KEY = 'domain'
CAOS_HYPERVISOR_TAG_KEY = 'hypervisor'
CAOS_PROJECT_TAG_KEY = 'project'


def _parse_cfg():
    _assign('SCHEDULERS', _get_schedulers())

    _assign('LOGGER_ROTATE_KEEP_COUNT',
            _get_int("logger.rotate_keep_count",
                     env_var="CAOS_COLLECTOR_LOGGER_ROTATE_KEEP_COUNT",
                     default=DEFAULT_LOGGER_ROTATE_KEEP_COUNT))

    _assign('LOGGER_LOG_FILE_PATH',
            _get_str("logger.log_file.path",
                     env_var="CAOS_COLLECTOR_LOGGER_LOG_FILE_PATH",
                     default=DEFAULT_LOGGER_LOG_FILE_PATH))

    _assign('LOGGER_ERROR_FILE_PATH',
            _get_str("logger.error_file.path",
                     env_var="CAOS_COLLECTOR_LOGGER_ERROR_FILE_PATH",
                     default=DEFAULT_LOGGER_ERROR_FILE_PATH))

    _assign('KEYSTONE_USERNAME',
            _get_str("keystone.username",
                     env_var="OS_USERNAME"))

    _assign('KEYSTONE_PASSWORD',
            _get_str("keystone.password",
                     env_var="OS_PASSWORD"))

    _assign('KEYSTONE_AUTH_URL',
            _get_str("keystone.auth_url",
                     env_var="OS_AUTH_URL"))

    _assign('KEYSTONE_PROJECT_ID',
            _get_str("keystone.project_id",
                     env_var="OS_PROJECT_ID",
                     required=False))

    _assign('KEYSTONE_PROJECT_NAME',
            _get_str("keystone.project_name",
                     env_var="OS_PROJECT_NAME",
                     required=False))

    _assign('KEYSTONE_DOMAIN_ID',
            _get_str("keystone.domain_id",
                     env_var="OS_DOMAIN_ID",
                     required=False))

    _assign('KEYSTONE_DOMAIN_NAME',
            _get_str("keystone.domain_name",
                     env_var="OS_DOMAIN_NAME",
                     required=False))

    _assign('KEYSTONE_USER_DOMAIN_ID',
            _get_str("keystone.user_domain_id",
                     env_var="OS_USER_DOMAIN_ID",
                     required=False))

    _assign('KEYSTONE_USER_DOMAIN_NAME',
            _get_str("keystone.user_domain_name",
                     env_var="OS_USER_DOMAIN_NAME",
                     required=False))

    _assign('KEYSTONE_PROJECT_DOMAIN_ID',
            _get_str("keystone.project_domain_id",
                     env_var="OS_PROJECT_DOMAIN_ID",
                     required=False))

    _assign('KEYSTONE_PROJECT_DOMAIN_NAME',
            _get_str("keystone.project_domain_name",
                     env_var="OS_PROJECT_DOMAIN_NAME",
                     required=False))

    _assign('KEYSTONE_CACERT',
            _get_str("keystone.cacert",
                     env_var="OS_CACERT"))

    _assign('KEYSTONE_API_VERSION',
            _get_str("keystone.identity_api_version",
                     env_var="OS_IDENTITY_API_VERSION",
                     default=DEFAULT_KEYSTONE_API_VERSION))

    # [openstack]
    _assign('OPENSTACK_VERSION',
            _get_str("openstack.version",
                     env_var="CAOS_COLLECTOR_OPENSTACK_VERSION",
                     default=DEFAULT_OPENSTACK_VERSION))

    _assign('OPENSTACK_PLACEMENT_API_VERSION',
            _get_str("openstack.placement.api_version",
                     env_var="OS_PLACEMENT_API_VERSION",
                     required=False,
                     default=DEFAULT_OPENSTACK_PLACEMENT_API_VERSION))

    _assign('OPENSTACK_PLACEMENT_ENDPOINT',
            _get_str("openstack.placement.endpoint",
                     env_var="CAOS_COLLECTOR_PLACEMENT_ENDPOINT",
                     required=False,
                     default=DEFAULT_OPENSTACK_PLACEMENT_ENDPOINT))

    _assign('OPENSTACK_NOVA_API_VERSION',
            _get_str("openstack.nova_api_version",
                     env_var="OS_COMPUTE_API_VERSION",
                     default=DEFAULT_OPENSTACK_NOVA_API_VERSION))

    # [caos-tsdb]
    _assign('CAOS_TSDB_API_URL',
            _get_str('caos-tsdb.api_url',
                     env_var="CAOS_COLLECTOR_TSDB_API_URL"))

    _assign('CAOS_TSDB_API_USERNAME',
            _get_str('caos-tsdb.username',
                     env_var="CAOS_COLLECTOR_TSDB_USERNAME"))

    _assign('CAOS_TSDB_API_PASSWORD',
            _get_str('caos-tsdb.password',
                     env_var="CAOS_COLLECTOR_TSDB_PASSWORD"))

    # [ceilometer]
    _assign('CEILOMETER_BACKEND',
            _get_str("ceilometer.backend",
                     env_var="CAOS_COLLECTOR_CEILOMETER_BACKEND",
                     default=DEFAULT_CEILOMETER_BACKEND,
                     required=False))

    _assign('CEILOMETER_MONGODB',
            _get_str('ceilometer.mongodb',
                     env_var="CAOS_COLLECTOR_MONGODB",
                     required=(CEILOMETER_BACKEND=='mongodb')))

    _assign('CEILOMETER_MONGODB_CONNECTION_TIMEOUT',
            _get_int('ceilometer.mongodb_connection_timeout',
                     env_var="CAOS_COLLECTOR_MONGODB_CONNECTION_TIMEOUT",
                     default=DEFAULT_CEILOMETER_MONGODB_CONNECTION_TIMEOUT,
                     required=False))

    _assign('CEILOMETER_POLLING_PERIOD',
            _get_int("ceilometer.polling_period",
                     env_var="CAOS_COLLECTOR_CEILOMETER_POLLING_PERIOD"))

    _assign('CEILOMETER_GNOCCHI_POLICY_GRANULARITY',
            _get_str('ceilometer.gnocchi.policy_granularity',
                     env_var="CAOS_COLLECTOR_CEILOMETER_GNOCCHI_POLICY_GRANULARITY",
                     default=DEFAULT_CEILOMETER_GNOCCHI_POLICY_GRANULARITY,
                     required=False))


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
    if _config is not None:
        raise RuntimeError("cfg file already parsed")

    if not os.path.exists(cfg_file) or not os.path.isfile(cfg_file):
        raise RuntimeError("cfg file '%s' doesn't exists" % cfg_file)

    with open(cfg_file, 'r') as ymlfile:
        _config = yaml.safe_load(ymlfile)

    _parse_cfg()


def _get(name, default=None, required=True, check_type=None, env_var=None):
    value = utils.deep_get(_config, name)

    if env_var and not value:
        value = os.getenv(env_var, None)

    value = value or default

    if required and not value:
        raise RuntimeError("Required option `{name}` not found in config file."
                           .format(name=name))

    if check_type and value is not None:
        try:
            value = utils.convert(value, check_type.__name__)
        except:
            raise RuntimeError("Cannot convert option `{name}` to `{type}`"
                               .format(name=name, type=check_type.__name__))

    return value


def _get_str(*args, **kwargs):
    return _get(*args, check_type=str, **kwargs)


def _get_int(*args, **kwargs):
    return _get(*args, check_type=int, **kwargs)


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
