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

from keystoneclient.auth.identity import v3
from keystoneauth1 import session
from keystoneclient import client as keystone_client
from keystoneclient import exceptions as keystone_client_exceptions
from novaclient import client as nova_client
from novaclient import exceptions as nova_client_exceptions

import cfg
import log


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


def get_nova_client():
    try:
        nova = nova_client.Client(session=_keystone_session,
                                  version=cfg.OPENSTACK_NOVA_API_VERSION)
        return nova
    except nova_client_exceptions.ClientException as e:
        raise OpenstackError(e)


def projects(domain_id=None):
    logger.debug("Querying projects from keystone...")
    keystone = get_keystone_client()
    if keystone.version == 'v3':
        keystone_projects = keystone.projects.list(domain=domain_id)
    elif keystone.version == 'v2':
        if domain_id:
            logger.warning("Domain filtering not implemented")
        keystone_projects = keystone.tenants.list()
    else:
        raise RuntimeError("Unknown keystoneclient version: '%s'" % keystone.version)
    keystone_projects = dict((p.id, p.to_dict()) for p in keystone_projects)
    return keystone_projects


def project(project_id):
    logger.debug("Querying project from keystone...")
    keystone = get_keystone_client()
    if keystone.version == 'v3':
        keystone_project = keystone.projects.get(project=project_id)
    else:
        raise RuntimeError("Unknown keystoneclient version: '%s'" % keystone.version)
    ret = {
        project_id: keystone_project.to_dict()
    }
    return ret


def domains():
    logger.debug("Querying domains from keystone...")
    keystone = get_keystone_client()
    keystone_domains = keystone.domains.list()
    keystone_domains = dict((d.id, d.to_dict()) for d in keystone_domains)
    return keystone_domains


def hypervisors(detailed=False):
    logger.debug("Querying hypervisors from nova...")
    nova = get_nova_client()

    nova_hypervisors = nova.hypervisors.list(detailed=detailed)
    nova_hypervisors = dict((h.hypervisor_hostname, h.to_dict()) for h in nova_hypervisors)
    return nova_hypervisors


def hypervisor_uptime(hypervisor):
    logger.debug("Querying hypervisor uptime from nova...")
    nova = get_nova_client()

    nova_uptime = nova.hypervisors.uptime(hypervisor=hypervisor)
    return nova_uptime.to_dict()


def project_quotas(project_id):
    logger.debug("Querying quota from nova...")
    nova = get_nova_client()

    nova_quota = nova.quotas.get(tenant_id=project_id)
    return nova_quota.to_dict()


def nova_usage(start, end, project_id):
    nova = get_nova_client()
    nova_usage = nova.usage.get(tenant_id=project_id,
                                start=start,
                                end=end)
    return nova_usage.to_dict()









#l =  nova.servers.list()
    #for i in l:
    #    print i


 #    search_opts={'all_tenants': 1})
 # def list(self, detailed=True, search_opts=None, marker=None, limit=None,
 #             sort_keys=None, sort_dirs=None):
 #        """
 #        Get a list of servers.

 #        :param detailed: Whether to return detailed server info (optional).
 #        :param search_opts: Search options to filter out servers (optional).
 #        :param marker: Begin returning servers that appear later in the server
 #                       list than that represented by this server id (optional).
 #        :param limit: Maximum number of servers to return (optional).
 #        :param sort_keys: List of sort keys
 #        :param sort_dirs: List of sort directions
