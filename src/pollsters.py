#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: pollster.py
# Created: 2016-07-12T12:56:39+0200
# Time-stamp: <2016-07-14T11:25:03cest>
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

from pymongo import ASCENDING, DESCENDING
from bson import SON

import log


logger = log.get_logger()


class Pollster(object):
    project_id = None
    metric_name = None
    period = None
    series_id = None
    ceilometer = None
    store = None
    start = None
    end = None

    def __init__(self, series, ceilometer, store, start, end):
        self.project_id = series['project_id']
        self.metric_name = series['metric_name']
        self.period = series['period']
        self.series_id = series['id']
        self.ceilometer = ceilometer
        self.store = store
        self.start = start
        self.end = end

    def run(self):
        # FIXME: check if a sample already exist
        #
        # We should check here only the last_timestamp field, and use
        # the following only in case of errors in store_sample
        s = self.store.samples(series_id=self.series_id,
                               timestamp=self.end)

        if len(s):
            logger.debug("Sample already exists, skipping")
            return

        self.do()

    def store_sample(self, value):
        ret = self.store.add_sample(series_id=self.series_id,
                                    timestamp=self.end,
                                    value=value)


class CPUPollster(Pollster):
    _COUNTER_NAME = "cpu"

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

    def do(self):
        resources = self.ceilometer.find_resources(project_id=self.project_id,
                                                   meter=self._COUNTER_NAME,
                                                   start=self.start, end=self.end)
        logger.debug("Project %s has %d resources" %(self.project_id, len(resources)))

        values = []
        for resource_id in resources:
            logger.debug("Aggregating %s for resource %s" % (self.metric_name, resource_id))
            v = self.aggregated_value(resource_id=resource_id,
                                      start=self.start,
                                      end=self.end,
                                      key='counter_volume')
            if not v:
                logger.debug("Missing %s data for resource %s" % (self.metric_name, resource_id))
                continue

            values.append(v)

        value = sum(values)
        self.store_sample(value)

    def build_query(self, resource_id, timestamp_query):
        return SON([
            ('resource_id', resource_id),
            ('project_id', self.project_id),
            ('counter_name', self._COUNTER_NAME),
            ('timestamp', timestamp_query),
            ('source', 'openstack')
        ])

    def interpolate_value(self, resource_id, timestamp, key):
        projection = {'timestamp': 1, key: 1}

        timestamp_query = {'$lte': timestamp}
        query = self.build_query(resource_id=resource_id, timestamp_query=timestamp_query)
        r1 = self.ceilometer.meter_db.find(query, projection).sort('timestamp', DESCENDING).limit(1)

        timestamp_query = {'$gt': timestamp}
        query = self.build_query(resource_id=resource_id, timestamp_query=timestamp_query)
        r2 = self.ceilometer.meter_db.find(query, projection).sort('timestamp', ASCENDING).limit(1)

        # FIXME: missing data
        #
        # At this point, due to the way ceilometer stores information
        # about resources (even after find_resources()), r1 and/or r2
        # could be empty, possibly due to:
        #
        #   - the instance has not yet been created
        #   - the instance has been just started
        #   - the instance has just been deleted
        #   - meter data is missing (e.g. ceilometer has been stopped)
        #
        # For the moment, we just return None
        if not r1.count(True) or not r2.count(True):
            return None

        t1 = r1[0]['timestamp']
        v1 = r1[0][key]

        t2 = r2[0]['timestamp']
        v2 = r2[0][key]

        t = timestamp
        dv = v2-v1
        dt = (t2-t1).total_seconds()
        v = v1 + dv/dt*((t-t1).total_seconds())
        return v

    def aggregated_value(self, resource_id, start, end, key):
        v1 = self.interpolate_value(resource_id=resource_id, timestamp=start, key=key)
        v2 = self.interpolate_value(resource_id=resource_id, timestamp=end, key=key)

        # FIXME: missing data (see interpolate_value)
        if not v1 or not v2:
            return None

        return v2-v1
