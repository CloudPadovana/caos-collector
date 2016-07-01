#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: store.py
# Created: 2016-07-01T10:09:26+0200
# Time-stamp: <2016-07-01T12:39:41cest>
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

    def _request(self, rest_type, api, json=None):
        f = getattr(requests, rest_type)
        url = "%s/%s" % (self.store_api_url, api)
        logger.debug("REST request: %s %s json=%s" % (rest_type, url, json))
        if json:
            return f(url, json)
        return f(url)

    def get(self, api):
        r = self._request('get', api)
        if not r.status_code == requests.codes.ok:
            return []
        return r.json()

    def put(self, api, json):
        r = self._request('put', api, json=json)
        return r.status_code == requests.codes.ok

    def post(self, api, json):
        r = self._request('post', api, json=json)
        return r.status_code == requests.codes.ok
