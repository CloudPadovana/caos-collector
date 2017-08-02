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
export CAOS_COLLECTOR_RELEASE_GIT_VERSION=$(ci-tools/git-describe.sh)

if [ -z "${PBR_VERSION}" ] ; then
    die "PBR_VERSION not set."
fi

if [ -z "${CAOS_COLLECTOR_RELEASE_GIT_VERSION}" ] ; then
    die "CAOS_COLLECTOR_RELEASE_GIT_VERSION not set."
fi

if [ "${DO_DOCKER_PUSH}" == true ] ; then
    say_yellow  "docker login"
    docker login -u ${CI_REGISTRY_USER} -p ${CI_REGISTRY_PASSWORD} ${CI_REGISTRY}
fi

CAOS_COLLECTOR_DOCKER_IMAGE_TAG=${CI_REGISTRY_IMAGE}:${CAOS_COLLECTOR_RELEASE_GIT_VERSION}

say_yellow  "Building docker container"
docker build \
       --tag ${CAOS_COLLECTOR_DOCKER_IMAGE_TAG} \
       --build-arg RELEASE_FILE="releases/caos_collector-${PBR_VERSION}-py2-none-any.whl" \
       --pull=true .

if [ "${DO_DOCKER_PUSH}" == true ] ; then
    say_yellow "Pushing container"
    docker push ${CAOS_COLLECTOR_DOCKER_IMAGE_TAG}
fi
