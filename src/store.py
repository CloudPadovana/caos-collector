#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: store.py
# Created: 2016-07-01T10:09:26+0200
# Time-stamp: <2016-07-07T12:13:37cest>
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

import log

import requests

logger = log.get_logger()


class Store:
    store_api_url = None

    class Result:
        def __init__(self, status_code, data):
            self.status_code = status_code
            self.data = data

        def ok(self):
            return (self.status_code == requests.codes.ok)

    def __init__(self, store_api_url):
        self.store_api_url = store_api_url

    def _request(self, rest_type, api, data=None, params=None):
        fun = getattr(requests, rest_type)
        url = "%s/%s" % (self.store_api_url, api)
        r = fun(url, json=data, params=params)
        logger.debug("REST request: %s %s params=%s json=%s" % (rest_type, url, params, data))
        ret = Store.Result(r.status_code, r.json())
        logger.debug("REST status: %s json=%s", ret.status_code, ret.data)
        return ret

    def get(self, api, params=None):
        r = self._request('get', api, params=params)
        if r.ok():
            return r.data['data']
        return []

    def put(self, api, data):
        r = self._request('put', api, data)
        return r.ok()

    def post(self, api, data):
        r = self._request('post', api, data)
        return r.ok()

    def projects(self):
        projects = self.get('projects')
        return dict((p['id'], p['name']) for p in projects)

    def project(self, id=None):
        if id:
            return self.get('projects/%s' % id)
        return self.projects

    def add_project(self, id, name=""):
        data = {
            'project': {
                'id': id,
                'name': name
            }
        }

        self.post('projects', data)

    def set_project(self, id, name=""):
        data = {
            'project': {
                'id': id,
                'name': name
            }
        }

        self.put('projects/%s' % id, data)

    def metrics(self):
        metrics = self.get('metrics')
        return dict((p['name'], p['type']) for p in metrics)

    def metric(self, name=None):
        if name:
            return self.get('metrics/%s' % name)
        return self.metrics

    def add_metric(self, name, type=""):
        data = {
            'metric': {
                'name': name,
                'type': type
            }
        }

        self.post('metrics', data)

    def set_metric(self, name, type=""):
        data = {
            'metric': {
                'name': name,
                'type': type
            }
        }

        self.put('metrics/%s' % name, data)

