#!/usr/bin/env python
# -*- coding: utf-8 -*-

################################################################################
#
# caos-collector - CAOS collector
#
# Copyright © 2017 INFN - Istituto Nazionale di Fisica Nucleare (Italy)
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

import requests_mock
import unittest

from caos_collector import cfg
from caos_collector import tsdb


CAOS_TSDB_API_ENDPOINT = "http://some-url"


def _mock_tsdb(m, verb, api, status_code=200, json=None, **kwargs):
    json = json or {}

    for key, value in kwargs.iteritems():
        if value:
            json[key] = value

    m.request(verb,
              CAOS_TSDB_API_ENDPOINT + "/" + api,
              status_code=status_code,
              json=json)


def mock_tsdb_get(m, *args, **kwargs):
    _mock_tsdb(m, 'GET', *args, **kwargs)


def mock_tsdb_post(m, *args, **kwargs):
    _mock_tsdb(m, 'POST', *args, **kwargs)


def mock_tsdb_graphql(m, *args, **kwargs):
    mock_tsdb_post(m, 'graphql', *args, **kwargs)


class TestTsdb(unittest.TestCase):
    def setUp(self):
        cfg.CAOS_TSDB_API_URL = CAOS_TSDB_API_ENDPOINT
        tsdb.initialize()

    def tearDown(self):
        pass

    @requests_mock.Mocker()
    def test_request_id(self, m):
        import logging
        from testfixtures import LogCapture

        mock_tsdb_graphql(m, data={'key': 'value'})
        with LogCapture(level=logging.DEBUG) as logs:
            tsdb.graphql("query")

            self.assertEqual(
                logs.records[0].msg,
                "GRAPHQL query=query, variables={}"
            )

            self.assertRegexpMatches(
                logs.records[1].msg,
                "^\[request_id=[a-z0-9-]{36}\] post http://some-url/graphql"
            )

            self.assertEqual(
                logs.records[2].msg,
                "[request_id=None] status=200, json={u'data': {u'key': u'value'}}"
            )

            self.assertEqual(
                logs.records[3].msg,
                "GRAPHQL response: json={u'data': {u'key': u'value'}}"
            )

    @requests_mock.Mocker()
    def test_api_status_ok(self, m):
        mock_tsdb_get(m, "status", data={'status': 'online'})
        status = tsdb.status()
        self.assertDictEqual(status, {'status': 'online'})

    @requests_mock.Mocker()
    def test_api_status_failure(self, m):
        mock_tsdb_get(m, "status", errors=['some error', ])
        status = tsdb.status()
        self.assertFalse(status)

    @requests_mock.Mocker()
    def test_api_token_ok(self, m):
        mock_tsdb_post(m, "token", data={'token': 'some_token'})
        token = tsdb.token("username", "password")
        self.assertEqual(token, "some_token")

    @requests_mock.Mocker()
    def test_api_token_not_ok(self, m):
        mock_tsdb_post(m, "token", data={'not_atoken': 'some_token'})
        with self.assertRaisesRegexp(tsdb.AuthError, "No token returned"):
            tsdb.token("username", "password")

    @requests_mock.Mocker()
    def test_api_token_failure(self, m):
        mock_tsdb_post(m, "token", errors=['error', ])
        with self.assertRaisesRegexp(tsdb.AuthError, "No token returned"):
            tsdb.token("username", "password")

    @requests_mock.Mocker()
    def test_graphql_ok(self, m):
        mock_tsdb_graphql(m, data={'key': 'value'})
        data = tsdb.graphql("query")
        self.assertEqual(data, {'key': 'value'})

    @requests_mock.Mocker()
    def test_graphql_with_errors(self, m):
        import logging
        from testfixtures import LogCapture

        mock_tsdb_graphql(m, data={'key': 'value'}, errors=[{'error': 'msg'}])
        with LogCapture(level=logging.ERROR) as logs:
            tsdb.graphql("query")
            logs.check(
                ('caos-collector.caos_collector.tsdb', 'ERROR', "GRAPHQL errors: [{u'error': u'msg'}]"),
            )

    @requests_mock.Mocker()
    def test_graphql_not_200(self, m):
        import logging
        from testfixtures import LogCapture

        mock_tsdb_graphql(m, status_code=401, data={'key': 'value'}, noerrors=[{'error': 'msg'}])
        with LogCapture(level=logging.WARNING) as logs:
            tsdb.graphql("query")
            logs.check(
                ('caos-collector.caos_collector.tsdb', 'WARNING', "GRAPHQL response code: 401"),
            )

    @requests_mock.Mocker()
    def test_graphql_failure(self, m):
        import logging

        from testfixtures import LogCapture
        mock_tsdb_graphql(m, nodata={'key': 'value'})
        with self.assertRaisesRegexp(tsdb.GraphqlError, "response has no `data`"):
            with LogCapture(level=logging.ERROR) as logs:
                tsdb.graphql("query")
                logs.check(
                    ('caos-collector.caos_collector.tsdb', 'ERROR', "GRAPHQL response has no `data`: raising..."),
                )
