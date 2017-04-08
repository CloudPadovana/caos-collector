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


class DomainsMetadataJob(Job):
    """The domains metadata job"""

    def __init__(self, *args, **kwargs):
        super(DomainsMetadataJob, self).__init__(
            name=__name__, *args, **kwargs)

    @staticmethod
    def setup_parser(parser):
        pass

    def _run(self, args):
        tz = datetime.datetime.utcnow()

        # get domains from keystone
        keystone_domains = openstack.domains()

        for domain_id, domain_data in keystone_domains.items():
            domain_name = domain_data['name']

            self.logger.info("Updating metadata for domain {id} ({name})"
                             .format(id=domain_id, name=domain_name))

            tsdb.create_tag_metadata(key=cfg.CAOS_DOMAIN_TAG_KEY,
                                     value=domain_id,
                                     metadata=domain_data,
                                     timestamp=tz)

        self.logger.info("Domains metadata updated")
