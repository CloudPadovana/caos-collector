#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: pollster.py
# Created: 2016-07-12T12:56:39+0200
# Time-stamp: <2016-08-05T09:59:10cest>
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
import datetime


import log
import caos_api
import ceilometer
import utils
import cfg


logger = log.get_logger()


class Pollster(object):
    project_id = None
    metric_name = None
    period = None
    series_id = None
    start = None
    end = None

    def __init__(self, series, start, end):
        self.project_id = series['project_id']
        self.metric_name = series['metric_name']
        self.period = series['period']
        self.series_id = series['id']
        self.start = start
        self.end = end


    def run(self, force_overwrite=False):
        value = self.measure()
        if value is None:
            logger.debug("Skipping null sample")
            return None

        sample = caos_api.add_sample(series_id=self.series_id,
                                     timestamp=self.end,
                                     value=value,
                                     force=force_overwrite)
        return sample


class CeilometerPollster(Pollster):
    counter_name = None
    ceilometer_polling_period = None

    def __init__(self, *args, **kwargs):
        super(CeilometerPollster, self).__init__(*args, **kwargs)

        self.counter_name = self._counter_name()
        self.ceilometer_polling_period = cfg.CEILOMETER_POLLING_PERIOD

    def _counter_name(self):
        raise NotImplementedError

    def _counter_value_field(self):
        return "counter_volume"

    def _projection(self):
        # by default do not project fields (i.e. return everything)
        return None

    def build_projection(self):
        projection = self._projection()
        if projection is not None:
            # we want to reduce fields, so let's start with what we surely need
            projection.update({
                'resource_id': 1,
                'timestamp': 1,
                self._counter_value_field(): 1
            })
        return projection

    def _samples_query(self):
        return []

    def find_resources(self):
        start = self.start - datetime.timedelta(seconds=self.ceilometer_polling_period)
        end = self.end + datetime.timedelta(seconds=self.ceilometer_polling_period)

        resources = ceilometer.find_resources(project_id=self.project_id,
                                              meter=self.counter_name,
                                              start=start, end=end)
        logger.debug("Project %s has %d resources of type %s in the range from %s to %s" % (self.project_id,
                                                                                            len(resources),
                                                                                            self.counter_name,
                                                                                            start,
                                                                                            end))
        return resources

    def build_query(self, resources, timestamp_query):
        query_list = []

        if type(resources) is str:
            query_list.append(('resource_id', resources))
        elif type(resources) is list:
            query_list.append(('resource_id', {
                '$in': resources
            }))
        else:
            raise RuntimeError("Wrong argument resources: %s of type %s" % (resources, type(resources)))

        query_list.extend([
            ('project_id', self.project_id),
            ('counter_name', self.counter_name),
            ('timestamp', timestamp_query),
            ('source', 'openstack')
        ])

        query_list.extend(self._samples_query())

        query = SON(query_list)
        return query

    def measure(self):
        # first test ceilometer_polling_period time guard
        now = datetime.datetime.utcnow()
        if now < self.end + datetime.timedelta(seconds=self.ceilometer_polling_period):
            return None

        resources = self.find_resources()

        # compute projection
        projection = self.build_projection()

        # To capture a proper value, we need to query the values
        # between time 'start' and 'end', plus a margin given by
        # ceilometer_polling_period. Then we interpolate according to
        # our period.
        timestamp_query = {
            '$gte': self.start - datetime.timedelta(seconds=self.ceilometer_polling_period),
            '$lte': self.end   + datetime.timedelta(seconds=self.ceilometer_polling_period)
        }

        # find samples
        query = self.build_query(resources, timestamp_query=timestamp_query)
        cursor = ceilometer.find("meter", query, projection).sort('timestamp', ASCENDING)
        allsamples = list(cursor)

        values = []
        for resource_id in resources:
            logger.debug("Aggregating %s for resource %s" % (self.metric_name, resource_id))

            samples = list(s for s in allsamples if s['resource_id'] == resource_id)
            v = self.aggregate_resource(samples, key=self._counter_value_field())
            if v is None:
                logger.debug("Missing %s data for resource %s" % (self.metric_name, resource_id))
                continue

            values.append(v)

        if not len(values):
            return None

        value = self.aggregate_values(values)
        return value

    @staticmethod
    def interpolate_value(samples, timestamp, key):
        epoch = utils.EPOCH

        x = list((s['timestamp']-epoch).total_seconds() for s in samples)
        y = list(s[key] for s in samples)

        x0 = (timestamp-epoch).total_seconds()
        y0 = utils.interp(x, y, x0)
        return y0

    @staticmethod
    def integrate_value(samples, key):
        epoch = utils.EPOCH

        x = list((s['timestamp']-epoch).total_seconds() for s in samples)
        y = list(s[key] for s in samples)

        I = utils.integrate(x, y)
        return I

    @staticmethod
    def flatten_mongo_data(d):
        if type(d) is dict:
            return dict(utils.flattenDict(d, join=lambda a,b: a+'.'+b))
        elif type(d) is list:
            return list(dict(utils.flattenDict(x, join=lambda a,b: a+'.'+b)) for x in d)
        else:
            raise RuntimeError("Don't know how to handle %s" % type(d))


class CPUPollster(CeilometerPollster):
    def __init__(self, *args, **kwargs):
        super(CPUPollster, self).__init__(*args, **kwargs)

    def _counter_name(self):
        return "cpu"

    def correct_monotonicity(self, items, key):
        # From the information we have, we just check if some value is
        # less than its predecessor. In this case we add a delta (also
        # to all the following values).
        delta = 0
        ret = []

        i0 = items[0]
        v0 = i0[key]
        ret.append(i0)
        for i in items[1:]:
            v = i[key]
            if v < v0:
                logger.debug("Correcting monotonicity: %s, %d < %s, %d", i ,v, i0, v0)
                # all the subsequent items will get the same correction
                delta += abs(v-v0)

            i[key] = v + delta
            ret.append(i)
            i0 = i
            v0 = v
        return ret

    def aggregate_resource(self, samples, key):
        # At this point, due to the way ceilometer stores information
        # about resources (even after find_resources()), data could be
        # missing, possibly due to:
        #
        #   - the instance has not yet been created
        #   - the instance has been just started
        #   - the instance has just been deleted
        #   - meter data is missing (e.g. ceilometer has been stopped)

        if len(samples) < 2:
            return None

        # NOTE: https://bugs.launchpad.net/ceilometer/+bug/1417949 Due
        # to a bug caused by libvirt, which resets the cputime on
        # instance rebuild, we also need to correct the monotonicity
        # of the samples.

        samples = self.correct_monotonicity(samples, key=key)

        v1 = self.interpolate_value(samples, timestamp=self.start, key=key)
        v2 = self.interpolate_value(samples, timestamp=self.end, key=key)

        ret = (v2-v1)/1e9
        return ret

    def aggregate_values(self, values):
        value = sum(values)
        return value



_pollsters = {
    'cpu': CPUPollster
}

def get_pollster(metric):
    return _pollsters[metric]

