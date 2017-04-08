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

import log
import tsdb


logger = log.get_logger(__name__)

DELTA_METRIC = {
    'type': 'delta'
}

GAUGE_METRIC = {
    'type': 'gauge'
}

METRIC_VM_CPU_TIME_USAGE       = 'cpu'
METRIC_VM_WALLCLOCK_TIME_USAGE = 'wallclocktime'
METRIC_VM_CPU_EFFICIENCY       = 'cpu.efficiency'

METRIC_VM_VCPUS_USAGE      = 'vm.vcpus.usage'
METRIC_VM_DISK_USAGE       = 'vm.disk.usage'
METRIC_VM_MEMORY_USAGE     = 'vm.memory.usage'
METRIC_VM_COUNT_ACTIVE     = 'vms.active'
METRIC_VM_COUNT_DELETED    = 'vms.deleted'

METRIC_QUOTA_MEMORY    = 'quota.memory'
METRIC_QUOTA_VCPUS     = 'quota.vcpus'
METRIC_QUOTA_INSTANCES = 'quota.instances'

## hypervisors
METRIC_HYPERVISOR_STATUS          = 'hypervisor.status'
METRIC_HYPERVISOR_STATE           = 'hypervisor.state'

METRIC_HYPERVISOR_CPUS_TOTAL      = 'hypervisor.cpus.total'
METRIC_HYPERVISOR_VCPUS_TOTAL     = 'hypervisor.vcpus.total'
METRIC_HYPERVISOR_VCPUS_USED      = 'hypervisor.vcpus.used'

METRIC_HYPERVISOR_RAM_TOTAL       = 'hypervisor.ram.total'
METRIC_HYPERVISOR_MEMORY_TOTAL    = 'hypervisor.memory.total'
METRIC_HYPERVISOR_MEMORY_USED     = 'hypervisor.memory.used'

METRIC_HYPERVISOR_RUNNING_VMS     = 'hypervisor.vms.running'
METRIC_HYPERVISOR_WORKLOAD        = 'hypervisor.workload'
METRIC_HYPERVISOR_LOAD_5m         = 'hypervisor.load.5m'
METRIC_HYPERVISOR_LOAD_10m        = 'hypervisor.load.10m'
METRIC_HYPERVISOR_LOAD_15m        = 'hypervisor.load.15m'

METRIC_HYPERVISOR_DISK_TOTAL      = 'hypervisor.disk.total'
METRIC_HYPERVISOR_DISK_USED       = 'hypervisor.disk.used'
METRIC_HYPERVISOR_DISK_FREE       = 'hypervisor.disk.free'
METRIC_HYPERVISOR_DISK_FREE_LEAST = 'hypervisor.disk.free.least'

METRICS = {
    METRIC_VM_CPU_TIME_USAGE: DELTA_METRIC,
    METRIC_VM_WALLCLOCK_TIME_USAGE: DELTA_METRIC,
    METRIC_VM_CPU_EFFICIENCY: GAUGE_METRIC,

    METRIC_VM_VCPUS_USAGE: DELTA_METRIC,
    METRIC_VM_DISK_USAGE: DELTA_METRIC,
    METRIC_VM_MEMORY_USAGE: DELTA_METRIC,
    METRIC_VM_COUNT_ACTIVE: GAUGE_METRIC,
    METRIC_VM_COUNT_DELETED: GAUGE_METRIC,

    METRIC_QUOTA_MEMORY: GAUGE_METRIC,
    METRIC_QUOTA_VCPUS: GAUGE_METRIC,
    METRIC_QUOTA_INSTANCES: GAUGE_METRIC,

    METRIC_HYPERVISOR_STATUS: GAUGE_METRIC,
    METRIC_HYPERVISOR_STATE: GAUGE_METRIC,

    METRIC_HYPERVISOR_CPUS_TOTAL: GAUGE_METRIC,
    METRIC_HYPERVISOR_VCPUS_TOTAL: GAUGE_METRIC,
    METRIC_HYPERVISOR_VCPUS_USED: GAUGE_METRIC,

    METRIC_HYPERVISOR_RAM_TOTAL: GAUGE_METRIC,
    METRIC_HYPERVISOR_MEMORY_TOTAL: GAUGE_METRIC,
    METRIC_HYPERVISOR_MEMORY_USED: GAUGE_METRIC,

    METRIC_HYPERVISOR_RUNNING_VMS: GAUGE_METRIC,
    METRIC_HYPERVISOR_WORKLOAD: GAUGE_METRIC,
    METRIC_HYPERVISOR_LOAD_5m: GAUGE_METRIC,
    METRIC_HYPERVISOR_LOAD_10m: GAUGE_METRIC,
    METRIC_HYPERVISOR_LOAD_15m: GAUGE_METRIC,

    METRIC_HYPERVISOR_DISK_TOTAL: GAUGE_METRIC,
    METRIC_HYPERVISOR_DISK_USED: GAUGE_METRIC,
    METRIC_HYPERVISOR_DISK_FREE: GAUGE_METRIC,
    METRIC_HYPERVISOR_DISK_FREE_LEAST: GAUGE_METRIC,

}


def check_metrics():
    metrics = tsdb.metrics()

    for m in METRICS:
        if m not in metrics:
            logger.info("Adding new metric {name}".format(name=m))
            tsdb.create_metric(name=m, type=METRICS[m]['type'])
