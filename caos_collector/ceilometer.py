#!/usr/bin/env python
# -*- coding: utf-8 -*-

################################################################################
#
# caos-collector - CAOS collector
#
# Copyright © 2016, 2017, 2018 INFN - Istituto Nazionale di Fisica Nucleare (Italy)
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

import pymongo
from bson import SON

import cfg
import log


logger = log.get_logger(__name__)


_ceilometer_backend = None


class ConnectionError(Exception):
    pass


class CeilometerBackend(object):
    logger = None

    def __init__(self, name, *args, **kwargs):
        self.logger = log.get_logger(name)

    def initialize(self):
        raise NotImplementedError

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def find_resources(self, *args, **kwargs):
        raise NotImplementedError

    def find(self, *args, **kwargs):
        raise NotImplementedError


class MongoCeilometerBackend(CeilometerBackend):
    _mongo = None
    _db = None

    def __init__(self, *args, **kwargs):
        super(MongoCeilometerBackend, self).__init__(
            name=__name__, *args, **kwargs)

    def initialize(self):
        mongodb = cfg.CEILOMETER_MONGODB
        connect_timeout = cfg.CEILOMETER_MONGODB_CONNECTION_TIMEOUT
        self.logger.info("Connecting to: %s." % mongodb)

        try:
            self._mongo = pymongo.MongoClient(
                mongodb,
                connectTimeoutMS=connect_timeout * 1000,
                serverSelectionTimeoutMS=connect_timeout * 1000)
            server_info = self._mongo.server_info()
        except pymongo.errors.ServerSelectionTimeoutError as e:
            raise ConnectionError(e)

        self.logger.debug(server_info)

        self._db = self._mongo.ceilometer

    def disconnect(self):
        if self._mongo:
            self.logger.info("Disconnecting from mongodb")
            self._mongo.close()

    def find(self, dbname, query, *args, **kwargs):
        self.logger.debug("Mongo query: %s" % query)
        db = getattr(self._db, dbname)
        return db.find(query, *args, **kwargs)

    def find_resources(self, project_id, meter, start=None, end=None):
        """ Find the resources in the given project that:
        - have a meter named __meter__
        - have at least one sample between start and end
        """

        # NOTE: on missing data
        #
        # Due to the way ceilometer stores information about resources, a
        # query to meter_db is necessary to be sure to have at least one
        # sample between start and end

        query_list = [
            ('project_id', project_id),
            ('source', 'openstack'),
            ('meter.counter_name', meter)
        ]

        if end is None and start is not None:
            self.logger.warn("find_resources: cannot ensure query order with end=None")

        if end is not None:
            query_list.append(
                ('first_sample_timestamp', {
                    '$lt': end
                }))

        if start is not None:
            query_list.append(
                ('last_sample_timestamp', {
                    '$gt': start
                }))

        query = SON(query_list)

        projection = {
            "_id": True
        }

        resources = self.find("resource", query, projection=projection)
        self.logger.debug("Got %d resources" % resources.count())
        ret = []
        for r in resources:
            ret.append(r['_id'])
        return ret


def initialize():
    global _ceilometer_backend
    backend = cfg.CEILOMETER_BACKEND

    if backend == 'mongodb':
        _ceilometer_backend = MongoCeilometerBackend()
    else:
        logger.error("Unknown ceilometer backend: {name}."
                     .format(name=backend))
    _ceilometer_backend.initialize()


def disconnect():
    global _ceilometer_backend
    if _ceilometer_backend:
        _ceilometer_backend.disconnect()


def find_resources(*args, **kwargs):
    global _ceilometer_backend
    return _ceilometer_backend.find_resources(*args, **kwargs)


def find(*args, **kwargs):
    global _ceilometer_backend
    return _ceilometer_backend.find(*args, **kwargs)
