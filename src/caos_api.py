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

import re
import requests
import semver


import cfg
import log
import utils


logger = log.get_logger(__name__)


_CAOS_API_SERVER_VERSION_RULES = [
    '==0.0.1',
]

_CAOS_API_VERSION_RULES = [
    '==1.0.0',
]

_REGEX = re.compile(
    r"""
    ^v
    (?P<major>(?:0|[1-9][0-9]*))
    (\.(?P<minor>(?:0|[1-9][0-9]*)))?
    $
    """, re.VERBOSE)

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

def initialize():
    global _caos_api_url

    _caos_api_url = cfg.CAOS_API_URL

def _check_version_rules(version, rules):
    ret = True
    for rule in rules:
        r = semver.match(version, rule)
        logger.debug("Checking if %s%s: %s", version, rule, "OK" if r else "Failed")
        ret = ret and r
    return ret

def check_version():
    api_status = status()
    ret = True

    # check server version
    version = api_status['version']
    logger.debug("Checking API server version %s...", version)
    ret = ret and _check_version_rules(version, _CAOS_API_SERVER_VERSION_RULES)
    if not ret:
        logger.error("Wrong API server version: %s", version)

    # check api version
    version = api_status['api_version']

    # normalize
    match = _REGEX.match(version)
    if match is None:
        logger.error("Invalid API version format: %s", version)
        return False
    major = match.group('major')
    minor = match.group('minor')

    version = semver.format_version(int(major),
                                    int(minor) if minor else 0,
                                    0)
    logger.debug("Checking API version %s...", version)
    ret = ret and _check_version_rules(version, _CAOS_API_VERSION_RULES)
    if not ret:
        logger.error("Wrong API version: %s", version)
    return ret

def set_token(token):
    global _token

    _token = token

def refresh_token():
    logger.info("Refreshing token...")
    new_token = token(username=cfg.CAOS_API_USERNAME,
                      password=cfg.CAOS_API_PASSWORD)
    logger.info("Got new token")

    set_token(new_token)
    api_status = status()
    logger.info("API is in status '%s'", api_status['status'])
    s = api_status['auth'] == "yes"
    if s:
        logger.info("API auth is OK")
    else:
        logger.error("Error with API auth")
    return s

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
