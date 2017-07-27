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

import unittest

from caos_collector import utils


class TestUtils(unittest.TestCase):
    def setUp(self):
        pass

    def test_interp(self):
        x = [1484783776.671, 1484784376.838, 1484784976.337,
             1484785576.466, 1484786176.598, 1484786776.324,
             1484787376.438, 1484787376.438, 1484787976.585]
        y = [228005050000000L, 228018210000000L, 228032540000000L,
             228047650000000L, 228063270000000L, 228078000000000L,
             228093390000000L, 228093390000000L, 228108420000000L]
        x0 = 1484784000.0
        y0 = utils.interp(x, y, x0)
        self.assertEqual(y0, 228009946986404.9)
