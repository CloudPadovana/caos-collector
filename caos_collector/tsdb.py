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

import datetime
import json
import re
import requests
import semver
from uuid import uuid4

import cfg
import log
import utils


logger = log.get_logger(__name__)


_CAOS_API_VERSION_RULES = [
    '>=1.2.0',
]

_REGEX = re.compile(
    r"""
    ^v
    (?P<major>(?:0|[1-9][0-9]*))
    (\.(?P<minor>(?:0|[1-9][0-9]*)))?
    $
    """, re.VERBOSE)

_REQUEST_ID_HTTP_HEADER = 'x-request-id'


class ConnectionError(Exception):
    pass


class AuthError(Exception):
    pass


class GraphqlError(Exception):
    pass


class JWTAuth(requests.auth.AuthBase):
    def __call__(self, r):
        r.headers['Authorization'] = "Bearer %s" % _token
        return r


__jwt_auth = JWTAuth()

_caos_tsdb_api_url = None
_token = None


def initialize():
    global _caos_tsdb_api_url

    if not _caos_tsdb_api_url:
        _caos_tsdb_api_url = cfg.CAOS_TSDB_API_URL


def _check_version_rules(version, rules):
    ret = True
    for rule in rules:
        r = semver.match(version, rule)
        logger.debug("Checking if {version}{rule}: {ret}"
                     .format(version=version,
                             rule=rule,
                             ret="OK" if r else "Failed"))
        ret = ret and r
    return ret


def check_version():
    api_status = status()
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
    ret = _check_version_rules(version, _CAOS_API_VERSION_RULES)
    if not ret:
        logger.error("Wrong API version: %s", version)
    return ret


def generate_request_id():
    return str(uuid4())


def get_request_id(request):
    if _REQUEST_ID_HTTP_HEADER in request.headers:
        return request.headers[_REQUEST_ID_HTTP_HEADER]
    return None


def set_token(token):
    global _token

    _token = token


def refresh_token():
    logger.info("Refreshing token...")
    new_token = token(username=cfg.CAOS_TSDB_API_USERNAME,
                      password=cfg.CAOS_TSDB_API_PASSWORD)
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


def _request(rest_type, api, data=None, params=None, return_data=True):
    fun = getattr(requests, rest_type)
    url = "%s/%s" % (_caos_tsdb_api_url, api)
    request_id = generate_request_id()

    headers = {
        _REQUEST_ID_HTTP_HEADER: request_id
    }

    logger.debug("[request_id={request_id}] {type} {url}, params={params}, json={json}"
                 .format(request_id=request_id, type=rest_type, url=url,
                         params=params, json=data))
    r = None
    try:
        r = fun(url, json=data, params=params, auth=__jwt_auth, headers=headers)
    except requests.exceptions.ConnectionError as e:
        raise ConnectionError(e)

    json = r.json()
    logger.debug("[request_id={request_id}] status={status}, json={json}"
                 .format(request_id=get_request_id(r),
                         status=r.status_code,
                         json=json))

    if return_data:
        data = {}
        if 'data' in json:
            data = json['data']
        return data
    else:
        return r


def get(api, *args, **kwargs):
    return _request(rest_type='get', api=api, *args, **kwargs)


def post(api, *args, **kwargs):
    return _request(rest_type='post', api=api, *args, **kwargs)


def graphql(query, variables={}):
    data = {
        'query': query,
        'variables': variables
    }

    logger.debug("GRAPHQL query={query}, variables={variables}"
                 .format(query=query, variables=variables))

    r = post('graphql', data=data, return_data=False)
    json = r.json()

    logger.debug("GRAPHQL response: json={json}".format(json=json))

    if 'errors' in json:
        logger.error("GRAPHQL errors: {errors}"
                     .format(errors=json['errors']))

    if r.status_code != 200:
        logger.warn("GRAPHQL response code: {code}".format(code=r.status_code))

    if 'data' not in json:
        logger.error("GRAPHQL response has no `data`: raising...")
        raise GraphqlError("GRAPHQL response has no `data`: json={json}"
                           .format(json=json))

    return json['data']


def status():
    return get('status')


def token(username, password):
    params = {
        'username': username,
        'password': password
    }

    data = post('token', data=params)
    if not data or 'token' not in data:
        raise AuthError("No token returned")

    token = data['token']
    return token


def tag(id=None, key=None, value=None):
    if id is not None:
        query = '''
        query {{
          tag(id: "{id}") {{
            id
            key
            value
          }}
        }}
        '''.format(id=id)
    else:
        query = '''
        query {{
          tag(key: "{key}", value: "{value}") {{
            id
            key
            value
          }}
        }}
        '''.format(key=key, value=value)

    return graphql(query)


def tags(key=None, value=None, with_metadata=False):
    query = '''
    query($key: String!, $value: String!, $latest: Boolean!) {
      tags(key: $key, value: $value) {
        id
        key
        value
        latest_metadata if $latest {
          timestamp
          metadata
        }
      }
    }
    '''

    variables = {
        'key': key,
        'value': value,
        'latest': with_metadata,
    }

    return graphql(query, variables)


def create_tag(key, value=""):
    query = '''
    mutation {{
      create_tag(key: "{key}", value: "{value}") {{
        id
        key
        value
      }}
    }}
    '''.format(key=key, value=value)

    logger.info("Creating new tag %s[%s]" % (key, value))
    graphql(query)


def create_tag_metadata(key, value, metadata, timestamp=None):
    if timestamp is None:
        timestamp = datetime.datetime.utcnow()

    query = '''
    mutation($tag: TagPrimary!, $metadata: String!, $timestamp: Datetime!) {
      metadata: create_tag_metadata(tag: $tag, metadata: $metadata, timestamp: $timestamp) {
        timestamp
        metadata
      }
    }
    '''  # noqa: E501

    variables = {
        'tag': {
            'key': key,
            'value': value
        },
        'metadata': json.dumps(metadata),
        'timestamp': utils.format_date(timestamp)
    }

    logger.info("Creating new tag metadata for tag {key}={value}[{metadata}]"
                .format(key=key, value=value, metadata=metadata))
    return graphql(query, variables)['metadata']


def metrics():
    query = '''
    query {
      metrics {
        name
        type
      }
    }
    '''

    metrics = graphql(query)['metrics']
    return dict((p['name'], p['type']) for p in metrics)


def create_metric(name, type=""):
    query = '''
    mutation {{
      metric: create_metric(name: "{name}", type: "{type}") {{
        name
        type
      }}
    }}
    '''.format(name=name, type=type)

    logger.info("Creating new metric %s" % name)
    return graphql(query)['metric']


def get_or_create_series(tags, metric_name, period):
    query = '''
mutation($period: Int!, $metric: MetricPrimary!, $tags: [TagPrimary!]!) {
  series: create_series(period: $period, metric: $metric, tags: $tags) {
    id
    period
    metric {
      name
    }
    tags {
      key
      value
    }
    last_timestamp
    ttl
  }
}
'''

    variables = {
        'metric': {
            'name': metric_name
        },
        'period': period,
        'tags': tags
    }

    r = graphql(query, variables)['series']
    return r


def create_sample(metric_name, period, tags, timestamp, value, overwrite=False):
    query = '''
mutation($series: SeriesPrimary!, $timestamp: Datetime!, $value: Float!, $overwrite: Boolean) {
  sample: create_sample(series: $series, timestamp: $timestamp, value: $value, overwrite: $overwrite) {
    timestamp
    value
  }
}
'''  # noqa: E501

    variables = {
        'series': {
            'metric': {
                'name': metric_name
            },
            'period': period,
            'tags': tags,
        },
        'timestamp': utils.format_date(timestamp),
        'value': value,
        'overwrite': overwrite,
    }

    logger.info("Creating new sample for metric {metric}, period {period}, "
                "tags {tags}, timestamp {timestamp}, value {value}, "
                "overwrite {overwrite}"
                .format(metric=metric_name,
                        period=period,
                        tags=tags,
                        timestamp=timestamp,
                        value=value,
                        overwrite=overwrite))

    return graphql(query, variables)['sample']


def last_timestamp(tags, metric_name, period):
    last_timestamp = get_or_create_series(tags=tags,
                                          metric_name=metric_name,
                                          period=period)['last_timestamp']

    if last_timestamp:
        last_timestamp = utils.parse_date(last_timestamp)
    else:
        # this happens when the series has no data
        logger.info("No previous data for tags {tags}, metric {m}, period {p}"
                    .format(tags=tags, m=metric_name, p=period))
        last_timestamp = utils.EPOCH

    return last_timestamp


def sample(tags, metric_name, period, timestamp):
    series_id = get_or_create_series(tags=tags,
                                     metric_name=metric_name,
                                     period=period)['id']

    query = '''
    query {{
      series(id: "{series_id}") {{
        sample(timestamp: "{timestamp}") {{
          timestamp
          value
        }}
      }}
    }}
    '''.format(series_id=series_id, timestamp=utils.format_date(timestamp))

    return graphql(query)['series']['sample']
