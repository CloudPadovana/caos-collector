#!/usr/bin/env python
# -*- coding: utf-8 -*-

################################################################################
#
# caos-collector - CAOS collector
#
# Copyright © 2017, 2018 INFN - Istituto Nazionale di Fisica Nucleare (Italy)
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
import re
import yaml

from job import Job
from caos_collector import cfg
from caos_collector import metrics
from caos_collector import openstack
from caos_collector import tsdb
from caos_collector import utils


_DEFAULT_ALLOCATION_RATIO = {
    'cpu': {
        'default': 1
    },
    'ram': {
        'default': 1
    }
}

_REGEX_LOADS = re.compile(".*load average:\s(.+),\s(.+),\s(.+)")


class HypervisorsStateJob(Job):
    """The hypervisors state job"""

    def __init__(self, *args, **kwargs):
        super(HypervisorsStateJob, self).__init__(
            name=__name__, *args, **kwargs)

    @staticmethod
    def setup_parser(parser):
        parser.add_argument(
            '-H', '--hypervisor',
            dest='hypervisor', metavar='ID',
            nargs='?',
            default=None,
            help='Limit by hypervisor')

        parser.add_argument(
            '-a', '--allocation-ratio',
            dest='allocation_ratio', metavar='YAML',
            nargs='?',
            default=None,
            type=yaml.load,
            help='Allocation ratios')

        parser.add_argument(
            '-n', '--no-placement',
            dest='no_placement',
            action='store_const',
            const=True,
            default=False,
            help='Don\'t query placement api (ocata and above)')

    def _run(self, args):
        tz = datetime.datetime.utcnow()

        ar = utils.deep_merge({}, _DEFAULT_ALLOCATION_RATIO)

        # query placement api if available and not disabled
        if cfg.OPENSTACK_VERSION >= 'ocata' and not args.no_placement:
            self.logger.info("Querying allocation ratios from placement API")
            placement_ar = self._query_ar_from_placement()
            self.logger.info("Allocation ratios from placement API: {ar}".format(
                ar=placement_ar))
            ar = utils.deep_merge(ar, placement_ar)

        # merge with values given on command-line
        if args.allocation_ratio:
            ar = utils.deep_merge(ar, args.allocation_ratio)

        # get hypervisors from nova
        hypervisors = openstack.hypervisors(detailed=True)

        hypervisor = args.hypervisor
        if hypervisor:
            hypervisors = {
                hypervisor: hypervisors[hypervisor]
            }

        for hypervisor_host, hypervisor_data in hypervisors.items():
            self.logger.info("Checking hypervisor state for hypervisor {name}"
                             .format(name=hypervisor_host))

            cpu_ar = self._get_allocation_ratio(ar, 'cpu', hypervisor_host)
            ram_ar = self._get_allocation_ratio(ar, 'ram', hypervisor_host)

            self.check_hypervisor(tz=tz, hypervisor_host=hypervisor_host,
                                  hypervisor_data=hypervisor_data,
                                  cpu_ar=cpu_ar, ram_ar=ram_ar)

        self.logger.info("Hypervisors state updated")

    def _query_ar_from_placement(self):
        ar = {
            'cpu': {},
            'ram': {},
        }

        placement = openstack.get_placement_client()

        providers = placement.resource_providers()
        for p in providers:
            uuid = p['uuid']
            name = p['name']

            cpu_inventory = placement.inventory(uuid, 'VCPU')
            ram_inventory = placement.inventory(uuid, 'MEMORY_MB')

            ar['cpu'][name] = cpu_inventory['allocation_ratio']
            ar['ram'][name] = ram_inventory['allocation_ratio']

        return ar

    def _get_allocation_ratio(self, arg, cpu_or_ram, hypervisor):
        map = arg[cpu_or_ram]
        ar = map['default']
        if hypervisor in map:
            ar = map[hypervisor]

        return ar

    def _get_hypervisor_load(self, hypervisor):
        data = openstack.hypervisor_uptime(hypervisor=hypervisor)
        if 'uptime' not in data:
            return None

        uptime = data['uptime']
        # Based on code from the openstack python client
        #
        # Extract data from uptime value
        # format: 0 up 0,  0 users,  load average: 0, 0, 0
        # example: 17:37:14 up  2:33,  3 users, load average: 0.33, 0.36, 0.34
        m = re.match(_REGEX_LOADS, uptime)
        if not m:
            return None

        try:
            loads = (
                float(m.group(1)),
                float(m.group(2)),
                float(m.group(3)),
            )
        except:
            loads = None
        return loads

    def check_hypervisor(self, tz, hypervisor_host, hypervisor_data,
                         cpu_ar, ram_ar):

        tag = {
            'key': cfg.CAOS_HYPERVISOR_TAG_KEY,
            'value': hypervisor_host
        }

        def add_sample(metric, value, tz=tz):
            tsdb.create_sample(metric_name=metric, period=0, tags=[tag],
                               timestamp=tz, value=value)

        h_status = 1 if hypervisor_data['status'] == 'enabled' else 0
        add_sample(metrics.METRIC_HYPERVISOR_STATUS, h_status)

        h_state = 1 if hypervisor_data['state'] == 'up' else 0
        add_sample(metrics.METRIC_HYPERVISOR_STATE, h_state)

        h_cpus = hypervisor_data['vcpus'] * h_status
        add_sample(metrics.METRIC_HYPERVISOR_CPUS_TOTAL, h_cpus)

        add_sample(metrics.METRIC_HYPERVISOR_VCPUS_TOTAL, h_cpus * cpu_ar)
        add_sample(
            metrics.METRIC_HYPERVISOR_VCPUS_USED,
            hypervisor_data['vcpus_used'])

        add_sample(
            metrics.METRIC_HYPERVISOR_RUNNING_VMS,
            hypervisor_data['running_vms'])

        h_ram = hypervisor_data['memory_mb'] * utils.u1_M * h_status
        add_sample(metrics.METRIC_HYPERVISOR_RAM_TOTAL, h_ram)
        add_sample(metrics.METRIC_HYPERVISOR_MEMORY_TOTAL, h_ram * ram_ar)
        add_sample(metrics.METRIC_HYPERVISOR_MEMORY_USED,
                   hypervisor_data['memory_mb_used'] * utils.u1_M)

        h_disk = hypervisor_data['local_gb'] * utils.u1_G * h_status
        add_sample(metrics.METRIC_HYPERVISOR_DISK_TOTAL, h_disk)
        add_sample(metrics.METRIC_HYPERVISOR_DISK_USED,
                   hypervisor_data['local_gb_used'] * utils.u1_G)
        add_sample(metrics.METRIC_HYPERVISOR_DISK_FREE,
                   hypervisor_data['free_disk_gb'] * utils.u1_G)
        add_sample(metrics.METRIC_HYPERVISOR_DISK_FREE_LEAST,
                   hypervisor_data['disk_available_least'] * utils.u1_G)

        add_sample(
            metrics.METRIC_HYPERVISOR_WORKLOAD,
            hypervisor_data['current_workload'])

        if not h_state:
            return
        tz = datetime.datetime.utcnow()
        h_loads = self._get_hypervisor_load(hypervisor_data['id'])
        if h_loads:
            (h_load_5m, h_load_10m, h_load_15m) = h_loads

            add_sample(metrics.METRIC_HYPERVISOR_LOAD_5m, h_load_5m, tz=tz)
            add_sample(metrics.METRIC_HYPERVISOR_LOAD_10m, h_load_10m, tz=tz)
            add_sample(metrics.METRIC_HYPERVISOR_LOAD_15m, h_load_15m, tz=tz)
