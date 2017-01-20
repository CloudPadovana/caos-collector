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

import pbr.version
import pkg_resources

__all__ = [
    '__package_name__',
    '__version__',
    '__description__',
    '__author__',
]

PACKAGE_NAME = 'caos-collector'
version_info = pbr.version.VersionInfo(PACKAGE_NAME)
pkg_info = pkg_resources.get_distribution(PACKAGE_NAME)


def _package_summary(lines, key):
    def is_matching_line(line):
        return line.lower().startswith(key.lower())

    matching_lines = filter(is_matching_line, lines)
    line = next(iter(matching_lines), '')
    _, _, value = line.partition(':')
    return value.strip() or None


def _get_from_pkg_info(key):
    lines = pkg_info._get_metadata(pkg_info.PKG_INFO)
    return _package_summary(lines, "%s:" % key)


__package_name__ = PACKAGE_NAME
__description__ = _get_from_pkg_info('Summary')
__author__ = _get_from_pkg_info('Author')


try:
    __version__ = version_info.version_string()
except AttributeError:
    __version__ = None
