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

export_version_vars

docker_login

CAOS_COLLECTOR_DOCKER_IMAGE_TAG=${CI_REGISTRY_IMAGE}:${CAOS_COLLECTOR_RELEASE_GIT_VERSION}

say_yellow  "Pulling docker container"
docker pull ${CAOS_COLLECTOR_DOCKER_IMAGE_TAG}-test

say_yellow  "Running docker container"
docker run --rm \
       ${CAOS_COLLECTOR_DOCKER_IMAGE_TAG}-test --help
