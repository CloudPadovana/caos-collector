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

from caos_collector import ceilometer
from caos_collector import log
from caos_collector import metrics
from caos_collector import openstack
from caos_collector import tsdb


class Job(object):
    _name = None
    logger = None

    def __init__(self, name, *args, **kwargs):
        self._name = name
        self.logger = log.get_logger(name)

    def name(self):
        return self._name

    @staticmethod
    def setup_parser(parser):
        raise NotImplementedError

    def _run(self, args):
        raise NotImplementedError

    def run_job(self, args):
        self._check_connectivity()

        ok = tsdb.refresh_token()
        if not ok:
            raise RuntimeError("TSDB API auth problems.")

        metrics.check_metrics()

        self._run(args)

    def _check_connectivity(self):
        tsdb.initialize()
        self.logger.info("Checking TSDB connectivity...")
        status = tsdb.status()
        self.logger.info("API server version %s is in status '%s'",
                         status['version'], status['status'])

        self.logger.info("Checking TSDB API version...")
        ok = tsdb.check_version()
        if not ok:
            raise RuntimeError("Wrong TSDB API. Exiting...")

        self.logger.info("Checking TSDB API auth...")
        ok = tsdb.refresh_token()
        if not ok:
            raise RuntimeError("Cannot authenticate to TSDB API. Exiting...")

        self.logger.info("Checking KEYSTONE auth...")
        openstack.initialize()
        openstack.get_keystone_client()

        self.logger.info("Checking ceilometer...")
        ceilometer.initialize()
