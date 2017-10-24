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

set -ex

ANSI_COLOR_GREEN="\033[32;1m"
ANSI_COLOR_RED="\033[31;1m"
ANSI_COLOR_YELLOW="\033[33;1m"
ANSI_RESET="\033[0;m"

function die () {
    format=${1:-""}
    shift
    printf >&2 "${ANSI_COLOR_RED}${format}${ANSI_RESET}\n" "$@"
    exit 1
}

function say () {
    format=${1:-""}
    shift
    printf "${format}\n" "$@"
}

function say_with_color () {
    color=$1
    format=$2
    shift 2
    say "${color}${format}${ANSI_RESET}" "$@"
}

function say_green () {
    say_with_color ${ANSI_COLOR_GREEN} "$@"
}

function say_red () {
    say_with_color ${ANSI_COLOR_RED} "$@"
}

function say_yellow () {
    say_with_color ${ANSI_COLOR_YELLOW} "$@"
}

function export_version_vars () {
    PBR_VERSION=$(ci-tools/git-semver-pbr.sh)
    RELEASE_GIT_VERSION=$(ci-tools/git-describe.sh)

    if [ -z "${PBR_VERSION}" ] ; then
        die "PBR_VERSION not set."
    fi

    if [ -z "${RELEASE_GIT_VERSION}" ] ; then
        die "RELEASE_GIT_VERSION not set."
    fi

    export PBR_VERSION="${PBR_VERSION}"
    export CAOS_COLLECTOR_RELEASE_GIT_VERSION="${RELEASE_GIT_VERSION}"
    export CAOS_COLLECTOR_DOCKER_IMAGE_TAG="${CI_REGISTRY_IMAGE}:${CAOS_COLLECTOR_RELEASE_GIT_VERSION}-${CI_COMMIT_REF_NAME}"
    export CAOS_COLLECTOR_RELEASE_DOCKER_IMAGE_TAG="${CI_REGISTRY_IMAGE}:${CAOS_COLLECTOR_RELEASE_GIT_VERSION}"
}

function docker_login () {
    if [ "${DO_DOCKER_LOGIN}" == true ] ; then
        say_yellow  "docker login to ${CI_REGISTRY}"
        docker login -u ${CI_REGISTRY_USER} -p ${CI_REGISTRY_PASSWORD} ${CI_REGISTRY}
    fi
}
