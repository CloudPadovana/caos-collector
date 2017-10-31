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

from pymongo import ASCENDING
from bson import SON
import datetime


import ceilometer
import cfg
import log
import utils


logger = log.get_logger(__name__)


class Pollster(object):
    period = None
    start = None
    end = None

    def __init__(self, period, start, end):
        self.period = period
        self.start = start
        self.end = end

    def measure(self):
        raise NotImplementedError


class CeilometerPollster(Pollster):
    project_id = None
    counter_name = None
    ceilometer_polling_period = None

    def __init__(self, project_id, *args, **kwargs):
        super(CeilometerPollster, self).__init__(*args, **kwargs)

        self.project_id = project_id
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
        start = (self.start
                 - datetime.timedelta(seconds=self.ceilometer_polling_period))
        end = (self.end
               + datetime.timedelta(seconds=self.ceilometer_polling_period))

        resources = ceilometer.find_resources(project_id=self.project_id,
                                              meter=self.counter_name,
                                              start=start, end=end)
        logger.debug("Project {id} has {n} resources of type {type} "
                     "in the range from {start} to {end}"
                     .format(id=self.project_id,
                             n=len(resources),
                             type=self.counter_name,
                             start=start,
                             end=end))
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
            raise RuntimeError(
                "Wrong argument resources: {resource} of type {type}"
                .format(resource=resources, type=type(resources)))

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
        resources = self.find_resources()

        # compute projection
        projection = self.build_projection()

        # To capture a proper value, we need to query the values
        # between time 'start' and 'end', plus a margin given by
        # ceilometer_polling_period. Then we interpolate according to
        # our period.
        timestamp_query = {
            '$gte': (
                self.start
                - datetime.timedelta(seconds=self.ceilometer_polling_period)
            ),
            '$lte': (
                self.end
                + datetime.timedelta(seconds=self.ceilometer_polling_period)
            )
        }

        # find samples
        query = self.build_query(resources, timestamp_query=timestamp_query)
        cursor = (ceilometer.find("meter", query, projection)
                  .sort('timestamp', ASCENDING))
        allsamples = list(cursor)

        if '.' in self._counter_value_field():
            allsamples = self.flatten_mongo_data(allsamples)

        values = []
        for resource_id in resources:
            logger.debug("Aggregating resource {id}"
                         .format(id=resource_id))

            samples = list(
                s for s in allsamples if s['resource_id'] == resource_id)
            v = self.aggregate_resource(samples,
                                        key=self._counter_value_field())
            if v is None:
                logger.debug("Missing data for resource {id}"
                             .format(id=resource_id))
                continue

            values.append(v)

        if not len(values):
            return None

        value = self.aggregate_values(values)
        return value

    def aggregate_resource(self, samples, key):
        values = list(s[key] for s in samples)
        value = sum(values)
        return value

    def aggregate_values(self, values):
        value = sum(values)
        return value

    @staticmethod
    def interpolate_value(samples, timestamp, key):
        epoch = utils.EPOCH

        x = list((s['timestamp'] - epoch).total_seconds() for s in samples)
        y = list(s[key] for s in samples)

        x0 = (timestamp - epoch).total_seconds()
        y0 = utils.interp(x, y, x0)
        return y0

    @staticmethod
    def integrate_value(samples, key):
        epoch = utils.EPOCH

        x = list((s['timestamp'] - epoch).total_seconds() for s in samples)
        y = list(s[key] for s in samples)

        I = utils.integrate(x, y)
        return I

    @staticmethod
    def flatten_mongo_data(d):
        if type(d) is dict:
            return dict(utils.flattenDict(d, join=lambda a, b: a + '.' + b))
        elif type(d) is list:
            return list(
                dict(utils.flattenDict(x, join=lambda a, b: a + '.' + b))
                for x in d)
        else:
            raise RuntimeError("Don't know how to handle %s" % type(d))


class CPUTimePollster(CeilometerPollster):
    def __init__(self, *args, **kwargs):
        super(CPUTimePollster, self).__init__(*args, **kwargs)

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
                logger.debug("Correcting monotonicity: %s, %d < %s, %d",
                             i, v, i0, v0)
                # all the subsequent items will get the same correction
                delta += abs(v - v0)

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

        ret = (v2 - v1) / 1e9
        return ret


class WallClockTimePollster(CeilometerPollster):
    def __init__(self, *args, **kwargs):
        super(WallClockTimePollster, self).__init__(*args, **kwargs)

    def _counter_name(self):
        return "instance"

    def _counter_value_field(self):
        return "resource_metadata.vcpus"

    def _projection(self):
        projection = {
            # 'resource_metadata.flavor.disk': 1,
            # 'resource_metadata.flavor.ephemeral': 1,
            # 'resource_metadata.flavor.ram': 1,
            # 'resource_metadata.flavor.vcpus': 1,
            'resource_metadata.status': 1,
            'resource_metadata.vcpus': 1
        }
        return projection

    def _samples_query(self):
        # instance samples are mixed with audit notification but we
        # can filter over resource_metadata.status == active (audit
        # notification on the other hand have the field
        # resource_metadata.state

        return [
            ('resource_metadata.status', 'active')
        ]

    def aggregate_resource(self, samples, key):
        if len(samples) < 2:
            return None

        # the integral
        I = self.integrate_value(samples, key=key)

        # fake samples at start and end
        s1 = samples[0]
        s2 = samples[-1]
        s1[key] = 0
        s2[key] = I

        v1 = self.interpolate_value([s1, s2], timestamp=self.start, key=key)
        v2 = self.interpolate_value([s1, s2], timestamp=self.end, key=key)

        ret = v2 - v1
        return ret
