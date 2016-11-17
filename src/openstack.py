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

from keystoneclient.auth.identity import v3
from keystoneauth1 import session
from keystoneclient import client as keystone_client
from keystoneclient import exceptions as keystone_client_exceptions

import cfg
import log
import utils


logger = log.get_logger(__name__)


_keystone_session = None


class OpenstackError(Exception):
    pass


def initialize():
    global _keystone_session

    os_envs = {
        'username'            : cfg.KEYSTONE_USERNAME,
        'password'            : cfg.KEYSTONE_PASSWORD,
        'auth_url'            : cfg.KEYSTONE_AUTH_URL,
        'project_id'          : cfg.KEYSTONE_PROJECT_ID,
        'project_name'        : cfg.KEYSTONE_PROJECT_NAME,
        'domain_id'           : cfg.KEYSTONE_DOMAIN_ID,
        'domain_name'         : cfg.KEYSTONE_DOMAIN_NAME,
        'user_domain_id'      : cfg.KEYSTONE_USER_DOMAIN_ID,
        'user_domain_name'    : cfg.KEYSTONE_USER_DOMAIN_NAME,
        'project_domain_id'   : cfg.KEYSTONE_PROJECT_DOMAIN_ID,
        'project_domain_name' : cfg.KEYSTONE_PROJECT_DOMAIN_NAME
    }

    auth = v3.Password(**os_envs)
    _keystone_session = session.Session(auth=auth, verify=cfg.KEYSTONE_CACERT)


def get_keystone_client():
    try:
        keystone = keystone_client.Client(session=_keystone_session,
                                          version=cfg.KEYSTONE_API_VERSION)
        return keystone
    except keystone_client_exceptions.ClientException as e:
        raise OpenstackError(e)


def projects():
    logger.debug("Querying projects from keystone...")
    keystone = get_keystone_client()
    if keystone.version == 'v3':
        keystone_projects = keystone.projects.list()
    elif keystone.version == 'v2':
        keystone_projects = keystone.tenants.list()
    else:
        raise RuntimeError("Unknown keystoneclient version: '%s'" % keystone.version)
    keystone_projects = dict((p.id, p.name) for p in keystone_projects)
    return keystone_projects
