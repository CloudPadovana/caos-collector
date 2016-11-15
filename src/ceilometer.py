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

import types
import warnings
import pymongo
from bson import SON

import cfg
import log


logger = log.get_logger()


_mongo = None
_db = None


class ConnectionError(Exception):
    pass

def initialize():
    mongodb = cfg.CEILOMETER_MONGODB
    connect_timeout = cfg.CEILOMETER_MONGODB_CONNECTION_TIMEOUT
    logger.info("Connecting to: %s." % mongodb)
    global _mongo
    try:
        _mongo = pymongo.MongoClient(mongodb,
                                     connectTimeoutMS=connect_timeout*1000,
                                     serverSelectionTimeoutMS=connect_timeout*1000)
        server_info = _mongo.server_info()
    except pymongo.errors.ServerSelectionTimeoutError as e:
        raise ConnectionError(e)

    logger.debug(server_info)

    global _db
    _db = _mongo.ceilometer


def disconnect():
    if _mongo:
        logger.info("Disconnecting from mongodb")
        _mongo.close()


def find(dbname, query, *args, **kwargs):
    logger.debug("Mongo query: %s" % query)
    db = getattr(_db, dbname)
    return db.find(query, *args, **kwargs)


def find_resources(project_id, meter, start=None, end=None):
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
        logger.warn("find_resources: cannot ensure query order with end=None")

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

    resources = find("resource", query, projection=projection)
    logger.debug("Got %d resources" % resources.count())
    ret = []
    for r in resources:
        ret.append(r['_id'])
    return ret
