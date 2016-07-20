#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: ceilometer.py
# Created: 2016-07-01T16:49:54+0200
# Time-stamp: <2016-07-20T12:54:50cest>
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
import types

import pymongo
from bson import SON


logger = log.get_logger()


_mongo = None
_db = None
_meter_db = None
_resource_db = None


def initialize(mongodb):
    logger.info("Connecting to: %s." % mongodb)
    global _mongo
    _mongo = pymongo.MongoClient(mongodb)
    logger.debug(_mongo.server_info())

    global _db
    _db = _mongo.ceilometer

    global _meter_db
    _meter_db = _db.meter

    global _resource_db
    _resource_db = _db.resource


def disconnect():
    if _mongo:
        logger.info("Disconnecting from mongodb")
        _mongo.close()


def meter_db():
    return _meter_db


def resource_db():
    return _resource_db


def find_resources(project_id, meter, start, end):
    """ Find the resources in the given project that:
    - have a meter named __meter__
    - have at least one sample between start and end
    """

    # FIXME: missing data (see CPUPollster)
    #
    # Due to the way ceilometer stores information about
    # resources, in order to be sure to have at least on sample
    # between start and end a query to the meter_db is necessary

    query = SON([
        ('project_id', project_id),
        ('source', 'openstack'),
        ('meter.counter_name', meter),
        ('first_sample_timestamp', {
            '$lt': end
        }),
        ('last_sample_timestamp', {
            '$gt': start
        })
    ])

    projection = {
        "_id": True
    }

    logger.debug("Mongo query: %s" % query)
    resources = _resource_db.find(query, projection=projection)
    logger.debug("Got %d resources" % resources.count())
    ret = []
    for r in resources:
        ret.append(r['_id'])
    return ret
