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

import requests

import log
import utils


logger = log.get_logger()

class ConnectionError(Exception):
    pass

class AuthError(Exception):
    pass

class JWTAuth(requests.auth.AuthBase):
    def __call__(self, r):
        r.headers['Authorization'] = "Bearer %s" % _token
        return r
__jwt_auth = JWTAuth()

_caos_api_url = None
_token = None

def initialize(caos_api_url):
    global _caos_api_url

    _caos_api_url = caos_api_url

def set_token(token):
    global _token

    _token = token


def _request(rest_type, api, data=None, params=None):
    fun = getattr(requests, rest_type)
    url = "%s/%s" % (_caos_api_url, api)

    r = None
    try:
        r = fun(url, json=data, params=params, auth=__jwt_auth)
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(e)

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

def status():
    return get('status')

def token(username, password):
    params = {
        'username': username,
        'password': password
    }

    data = post('token', data=params)
    if not data or not 'token' in data:
        raise AuthError("No token returned")

    token = data['token']
    return token

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

def series_grid(series_id, from_date=None):
    params = {}
    if from_date:
        params['from'] = utils.format_date(from_date)

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
