#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: store.py
# Created: 2016-07-01T10:09:26+0200
# Time-stamp: <2016-07-14T11:17:48cest>
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

    def __init__(self, store_api_url):
        self.store_api_url = store_api_url

    def _format_date(self, date):
        return date.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _request(self, rest_type, api, data=None, params=None):
        fun = getattr(requests, rest_type)
        url = "%s/%s" % (self.store_api_url, api)
        r = fun(url, json=data, params=params)
        logger.debug("REST request: %s %s params=%s json=%s" % (rest_type, url, params, data))
        json = r.json()
        logger.debug("REST status: %s json=%s", r.status_code, json)

        if r.ok and 'data' in json:
            return json['data']
        return r.ok

    def get(self, api, params=None):
        return self._request('get', api, params=params)

    def put(self, api, data):
        return self.post(api, data, request='put')

    def post(self, api, data, request='post'):
        return self._request(request, api, data)

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

    def series(self, id=None):
        if id:
            return self.get('series/%s' % id)
        series = self.get('series')
        return dict((p['id'], [p['project_id'], p['metric_name'], p['period']]) for p in series)

    def series_by(self, project_id=None, metric_name=None, period=None):
        params = {}
        if project_id:
            params['project_id'] = project_id
        if metric_name:
            params['metric_name'] = metric_name
        if period:
            params['period'] = period

        return self.get('series', params=params)

    def create_series(self, project_id, metric_name, period):
        data = {
            'series': {
                'project_id': project_id,
                'metric_name': metric_name,
                'period': period
            }
        }

        return self.post('series', data)

    def add_sample(self, series_id, timestamp, value):
        data = {
            'sample': {
                'series_id': series_id,
                'timestamp': self._format_date(timestamp),
                'value': value,
            }
        }

        return self.post('samples', data)

    def samples(self, series_id=None, timestamp=None):
        params = {}
        if series_id:
            params['series_id'] = series_id
        if timestamp:
            params['timestamp'] = self._format_date(timestamp)

        return self.get('samples', params=params)
