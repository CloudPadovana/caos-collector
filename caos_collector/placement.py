#!/usr/bin/env python
# -*- coding: utf-8 -*-

################################################################################
#
# caos-collector - CAOS collector
#
# Copyright © 2018 INFN - Istituto Nazionale di Fisica Nucleare (Italy)
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

import cfg
import log

# Based on https://github.com/openstack/osc-placement/blob/master/osc_placement/http.py

import contextlib
import json

import keystoneauth1.exceptions.http as ks_exceptions
import osc_lib.exceptions as exceptions
import osc_lib.utils as utils
import six


logger = log.get_logger(__name__)


_http_error_to_exc = {
    cls.http_status: cls
    for cls in exceptions.ClientException.__subclasses__()
}

PLACEMENT_NAME = 'placement'

ENDPOINT_FILTER = {
    'service_type': PLACEMENT_NAME,
    'service_name': PLACEMENT_NAME,
    # 'interface': 'admin',
    # 'region_name': 'regionOne'
}


@contextlib.contextmanager
def _wrap_http_exceptions():
    """Reraise osc-lib exceptions with detailed messages."""

    try:
        yield
    except ks_exceptions.HttpError as exc:
        detail = json.loads(exc.response.content)['errors'][0]['detail']
        msg = detail.split('\n')[-1].strip()
        exc_class = _http_error_to_exc.get(exc.http_status,
                                           exceptions.CommandError)

        six.raise_from(exc_class(exc.http_status, msg), exc)


class PlacementSessionClient(object):
    def __init__(self, session, version):
        self.session = session
        self.version = version

    def request(self, method, url, **kwargs):
        api_version = "{service} {version}".format(
            service=PLACEMENT_NAME, version=self.version)

        headers = kwargs.pop('headers', {})
        headers.setdefault('OpenStack-API-Version', api_version)
        headers.setdefault('Accept', 'application/json')

        with _wrap_http_exceptions():
            return self.session.request(
                url, method,
                headers=headers,
                endpoint_filter=ENDPOINT_FILTER,
                endpoint_override=cfg.OPENSTACK_PLACEMENT_ENDPOINT,
                **kwargs)

    def get(self, url, **kwargs):
        return self.request('GET', url)

    def resource_providers(self):
        URL = '/resource_providers'
        data = self.get(URL).json()
        resources = utils.get_field(data, 'resource_providers')

        return resources

    def inventory(self, uuid, resource_class):
        URL = '/resource_providers/{uuid}/inventories/{resource_class}'.format(
            uuid=uuid, resource_class=resource_class)
        data = self.get(URL).json()
        return data
