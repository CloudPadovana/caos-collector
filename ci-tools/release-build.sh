#!/usr/bin/env bash

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

set -e

source ${CI_PROJECT_DIR}/ci-tools/common.sh

export PBR_VERSION=$(ci-tools/git-semver-pbr.sh)

if [ -z "${PBR_VERSION}" ] ; then
    die "PBR_VERSION not set."
fi

say_yellow  "Building release"
python setup.py bdist_wheel -v

RELEASES_DIR=${CI_PROJECT_DIR}/releases
if [ ! -d "${RELEASES_DIR}" ] ; then
    say_yellow  "Creating releases directory"
    mkdir ${RELEASES_DIR}
fi

say_yellow  "Copying release file"
cp -v dist/caos_collector-${PBR_VERSION}-py2-none-any.whl ${RELEASES_DIR}/
