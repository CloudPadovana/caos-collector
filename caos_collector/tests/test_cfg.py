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

import mock
import os
import unittest


from caos_collector import cfg


class TestCfg(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @mock.patch('caos_collector.cfg._config', {})
    def test_read_again(self):
        with self.assertRaisesRegexp(RuntimeError, "cfg file already parsed"):
            cfg.read("some file")

        reload(cfg)
        self.assertIsNone(cfg._config)

    def test_read_non_existent_file(self):
        with self.assertRaisesRegexp(RuntimeError, "cfg file '.*' doesn't exists"):
            cfg.read("non_existent_file.yaml")


    @mock.patch('caos_collector.cfg._config', {'int_var': 1, 'str_int_var': '2', 'str_var': "str"})
    def test_get_int(self):
        value = cfg._get_int("int_var")
        self.assertIs(type(value), int)
        self.assertEqual(value, 1)

        value = cfg._get_int("str_int_var")
        self.assertIs(type(value), int)
        self.assertEqual(value, 2)

        with self.assertRaisesRegexp(RuntimeError, "Cannot convert option `str_var` to `int`"):
            cfg._get_int("str_var")

    @mock.patch('caos_collector.cfg._config', {'int_var': 1, 'str_int_var': '2', 'str_var': "str"})
    def test_get_int_or_str(self):
        value = cfg._get_int_or_str("int_var")
        self.assertIs(type(value), int)
        self.assertEqual(value, 1)

        value = cfg._get_int_or_str("str_int_var")
        self.assertIs(type(value), int)
        self.assertEqual(value, 2)

        value = cfg._get_int_or_str("str_var")
        self.assertIs(type(value), str)
        self.assertEqual(value, "str")

    @mock.patch('caos_collector.cfg._config', {'my_var': 23})
    def test_get_int_with_default(self):
        value = cfg._get_int("my_var", default=56, required=False)
        self.assertEqual(value, 23)

        value = cfg._get_int("my_other_var", default=56, required=False)
        self.assertEqual(value, 56)

        with self.assertRaisesRegexp(RuntimeError, "Cannot convert option `my_other_var` to `int`"):
            cfg._get_int("my_other_var", default='56a', required=False)

    @mock.patch('caos_collector.cfg._config', {'my_var': 23})
    def test_get_int_without_default(self):
        value = cfg._get_int("my_var", default=None, required=False)
        self.assertEqual(value, 23)

        value = cfg._get_int("my_other_var", default=None, required=False)
        self.assertIsNone(value)

    @mock.patch('caos_collector.cfg._config', {'my_var': 23})
    def test_get_int_required_with_default(self):
        value = cfg._get_int("my_var", default=56, required=True)
        self.assertEqual(value, 23)

        value = cfg._get_int("my_other_var", default=56, required=True)
        self.assertEqual(value, 56)

        with self.assertRaisesRegexp(RuntimeError, "Cannot convert option `.*` to `int`"):
            cfg._get_int("my_other_var", default='56a', required=True)

    @mock.patch('caos_collector.cfg._config', {'my_var': 23})
    def test_get_int_required_without_default(self):
        value = cfg._get_int("my_var", default=None, required=True)
        self.assertEqual(value, 23)

        with self.assertRaisesRegexp(RuntimeError, "Required option `.*` not found"):
            cfg._get_int("my_other_var", default=None, required=True)
