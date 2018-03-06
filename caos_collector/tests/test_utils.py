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

    def test_convert(self):
        cases = [
            ("5", int, 5),
            ("5", str, "5"),
            ("5", float, 5.0),
        ]

        for case in cases:
            src_value = case[0]
            type_ = case[1]
            dst_value = case[2]

            value = utils.convert(src_value, type_.__name__)
            self.assertEqual(value, dst_value)
            self.assertIs(type(value), type_)

    def test_convert_fails(self):
        cases = [
            ("5a", int),
            ("5a", float),
        ]

        for case in cases:
            src_value = case[0]
            type_ = case[1]

            with self.assertRaises(Exception):
                value = utils.convert(src_value, type_.__name__)

    def test_deep_merge(self):
        a = {
            1: {"a": "A"},
            2: {"b": "B"},
            'c': 3,
        }
        b = {
            'c': 7,
            2: {"c": "C"},
            3: {"d": "D"},
        }

        expected = {
            1: {"a": "A"},
            'c': 7,
            2: {"b": "B", "c": "C"},
            3: {"d": "D"},
        }

        value = utils.deep_merge(a, b)
        self.assertEqual(value, expected)
