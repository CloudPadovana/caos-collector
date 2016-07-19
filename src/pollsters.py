#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: pollster.py
# Created: 2016-07-12T12:56:39+0200
# Time-stamp: <2016-07-19T16:32:30cest>
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
import apistorage


logger = log.get_logger()


class Pollster(object):
    project_id = None
    metric_name = None
    period = None
    series_id = None
    ceilometer = None
    start = None
    end = None

    def __init__(self, series, ceilometer, start, end):
        self.project_id = series['project_id']
        self.metric_name = series['metric_name']
        self.period = series['period']
        self.series_id = series['id']
        self.ceilometer = ceilometer
        self.start = start
        self.end = end

    def run(self):
        # FIXME: check if a sample already exist
        #
        # We should check here only the last_timestamp field, and use
        # the following only in case of errors in store_sample
        s = apistorage.sample(series_id=self.series_id,
                              timestamp=self.end)

        if len(s):
            logger.debug("Sample already exists, skipping")
        else:
            self.do()

        # FIXME: get last_timestamp from apistorage
        last_timestamp = self.end
        return last_timestamp

    def store_sample(self, value):
        ret = apistorage.add_sample(series_id=self.series_id,
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
            v = self.aggregate_values(resource_id=resource_id,
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

    def interpolate_value(self, r1, r2, timestamp, key):
        t1 = r1['timestamp']
        v1 = r1[key]

        t2 = r2['timestamp']
        v2 = r2[key]

        t = timestamp
        dv = v2-v1
        dt = (t2-t1).total_seconds()
        v = v1 + dv/dt*((t-t1).total_seconds())
        return v
    def correct_monotonicity(self, items, key):
        # From the information we have, we just check if some value is
        # less than its predecessor. In this case we add a delta (also
        # to all the following values).

        delta = 0

        i0 = items[0]
        v0 = i0[key]
        for i in items[1:]:
            v = i[key]
            if v < v0:
                logger.debug("Correcting monotonicity: %s, %d < %s, %d",i ,v, i0, v0)
                delta += abs(v-v0)

                # all the subsequent items will get the same correction
                items[0][key] = v + delta
            i0 = i
            v0 = v
        return items

    def aggregate_values(self, resource_id, start, end, key):
        # To capture a proper value for CPU time, we need to query the
        # values between time 'start' (exclusive) and 'end'
        # (inclusive). We also need to capture the two points at the
        # edges to interpolate according to our period.
        #
        # Moreover, due to bug
        # https://bugs.launchpad.net/ceilometer/+bug/1417949, caused
        # by libvirt resetting the cputime on instance rebuild, we
        # also need to correct the monotonicity of the samples.

        projection = {'timestamp': 1,
                      key: 1,
                      'resource_metadata.cpu_number': 1}

        # left edge
        timestamp_query = {'$lte': start}
        query = self.build_query(resource_id=resource_id, timestamp_query=timestamp_query)
        r1 = self.ceilometer.meter_db.find(query, projection).sort('timestamp', DESCENDING).limit(1)

        # data
        timestamp_query = {'$gt': start,
                           '$lte': end}
        query = self.build_query(resource_id=resource_id, timestamp_query=timestamp_query)
        r2 = self.ceilometer.meter_db.find(query, projection).sort('timestamp', ASCENDING)

        # right edge
        timestamp_query = {'$gt': end}
        query = self.build_query(resource_id=resource_id, timestamp_query=timestamp_query)
        r3 = self.ceilometer.meter_db.find(query, projection).sort('timestamp', ASCENDING).limit(1)

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
        if not r1.count(with_limit_and_skip=True) or not r3.count(with_limit_and_skip=True):
            return None

        r = []
        r.append(r1[0])
        r.extend(list(r2))
        r.append(r3[0])

        r = self.correct_monotonicity(r, key=key)

        v1 = self.interpolate_value(r[0], r[1], timestamp=start, key=key)
        v2 = self.interpolate_value(r[-2], r[-1], timestamp=end, key=key)

        return (v2-v1)/1e9
