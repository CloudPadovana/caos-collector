#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: caos_api.py
# Created: 2016-07-01T10:09:26+0200
# Time-stamp: <2016-07-29T12:48:21cest>
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

import requests

import log
import utils


logger = log.get_logger()


_caos_api_url = None


def initialize(caos_api_url):
    global _caos_api_url

    _caos_api_url = caos_api_url

def _request(rest_type, api, data=None, params=None):
    fun = getattr(requests, rest_type)
    url = "%s/%s" % (_caos_api_url, api)
    r = fun(url, json=data, params=params)
    logger.debug("REST request: %s %s params=%s json=%s" % (rest_type, url, params, data))
    json = r.json()
    logger.debug("REST status: %s json=%s", r.status_code, json)

    if r.ok and 'data' in json:
        return json['data']
    return r.ok

def get(api, params=None):
    return _request('get', api, params=params)

def put(api, data):
    return post(api, data, request='put')

def post(api, data, request='post'):
    return _request(request, api, data)

def projects():
    projects = get('projects')
    return dict((p['id'], p['name']) for p in projects)

def project(id=None):
    if id:
        return get('projects/%s' % id)
    return projects

def add_project(id, name=""):
    data = {
        'project': {
            'id': id,
            'name': name
        }
    }

    post('projects', data)

def set_project(id, name=""):
    data = {
        'project': {
            'id': id,
            'name': name
        }
    }

    put('projects/%s' % id, data)

def metrics():
    metrics = get('metrics')
    return dict((p['name'], p['type']) for p in metrics)

def metric(name=None):
    if name:
        return get('metrics/%s' % name)
    return metrics

def add_metric(name, type=""):
    data = {
        'metric': {
            'name': name,
            'type': type
        }
    }

    post('metrics', data)

def set_metric(name, type=""):
    data = {
        'metric': {
            'name': name,
            'type': type
        }
    }

    put('metrics/%s' % name, data)

def _process_series(series):
    if not type(series) is list:
        series = [series, ]

    ret = []
    for s in series:
        i = dict((p, s[p]) for p in s)
        if i['last_timestamp']:
            i['last_timestamp'] = utils.parse_date(i['last_timestamp'])
        ret.append(i)
    return ret

def series(id=None, project_id=None, metric_name=None, period=None):
    if id:
        r = get('series/%s' % id)
        return _process_series(r)

    params = {}
    if project_id:
        params['project_id'] = project_id
    if metric_name:
        params['metric_name'] = metric_name
    if period:
        params['period'] = period

    r = get('series', params=params)
    return _process_series(r)

def create_series(project_id, metric_name, period):
    data = {
        'series': {
            'project_id': project_id,
            'metric_name': metric_name,
            'period': period
        }
    }

    return post('series', data)

def series_grid(series_id, start_date=None):
    params = {}
    if start_date:
        params['start_date'] = utils.format_date(start_date)

    r = get('series/%d/grid' % series_id, params=params)['grid']
    return list(utils.parse_date(v) for v in r)

def add_sample(series_id, timestamp, value, force=False):
    data = {
        'sample': {
            'series_id': series_id,
            'timestamp': utils.format_date(timestamp),
            'value': value,
        }
    }

    if force:
        data['sample']['force'] = True

    return post('samples', data)

def samples(series_id=None, timestamp=None):
    params = {}
    if series_id:
        params['series_id'] = series_id
    if timestamp:
        params['timestamp'] = utils.format_date(timestamp)

    return get('samples', params=params)
