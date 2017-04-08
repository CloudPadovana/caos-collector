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

import datetime

from job import Job
from caos_collector import cfg
from caos_collector import openstack
from caos_collector import tsdb


_HYPERVISOR_FIELDS = (
    'vcpus',
    'host_ip',
    'hypervisor_type',
    'service',
    'state',
    'status',
)


class HypervisorsMetadataJob(Job):
    """The hypervisors metadata job"""

    def __init__(self, *args, **kwargs):
        super(HypervisorsMetadataJob, self).__init__(
            name=__name__, *args, **kwargs)

    @staticmethod
    def setup_parser(parser):
        pass

    def _run(self, args):
        tz = datetime.datetime.utcnow()

        # get hypervisors from nova
        hypervisors = openstack.hypervisors(detailed=True)

        for hypervisor_host, hypervisor_data in hypervisors.items():
            self.logger.info("Updating metadata for hypervisor {name}"
                             .format(name=hypervisor_host))

            data = {k: hypervisor_data[k] for k in _HYPERVISOR_FIELDS}

            tsdb.create_tag_metadata(key=cfg.CAOS_HYPERVISOR_TAG_KEY,
                                     value=hypervisor_host,
                                     metadata=data,
                                     timestamp=tz)

        self.logger.info("Hypervisors metadata updated")
