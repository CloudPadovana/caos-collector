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


class ProjectsMetadataJob(Job):
    """The projects metadata job"""

    def __init__(self, *args, **kwargs):
        super(ProjectsMetadataJob, self).__init__(
            name=__name__, *args, **kwargs)

    @staticmethod
    def setup_parser(parser):
        parser.add_argument(
            '-d', '--domain',
            dest='domain_id', metavar='ID',
            nargs='?',
            default=None,
            help='Limit by domain id')

    def _run(self, args):
        domain_id = args.domain_id

        tz = datetime.datetime.utcnow()

        # get projects from keystone
        keystone_projects = openstack.projects(domain_id=domain_id)

        for project_id, project_data in keystone_projects.items():
            project_name = project_data['name']

            self.logger.info("Updating metadata for project {id} ({name})"
                             .format(id=project_id, name=project_name))

            tsdb.create_tag_metadata(key=cfg.CAOS_PROJECT_TAG_KEY,
                                     value=project_id,
                                     metadata=project_data,
                                     timestamp=tz)

        self.logger.info("Projects metadata updated")
