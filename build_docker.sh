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

PROJECT_DIR=$(dirname $(readlink -f $0))
source ${PROJECT_DIR}/ci-tools/common.sh

GIT_SHA=$(git rev-parse --verify HEAD)
DOCKER_BUILD_IMAGE="docker:stable"
DOCKER_DIND_BUILD_IMAGE="docker:stable-dind"

releases_dir=releases

dind_container_id=$(docker run --privileged -t -d ${DOCKER_DIND_BUILD_IMAGE})
say "Started container: %s\n" ${dind_container_id}

container_id=$(docker run -t -d \
                      --link ${dind_container_id}:docker \
                      -v $(readlink -e $(pwd)):/origin:ro -v /build -w /build \
                      ${DOCKER_BUILD_IMAGE})
say "Started container: %s\n" ${container_id}

function docker_exec () {
    # docker-entrypoint.sh is called only on docker run, and it sets
    # DOCKER_HOST to connect to dind container, which for some reason
    # is reset by subsequent docker execs.  As a workaround let's call
    # the entrypoint on docker exec.

    docker exec \
           -e "CI_PROJECT_DIR=/build" \
           -e "CI_COMMIT_SHA=${GIT_SHA}" \
           -e "CI_REGISTRY_IMAGE=caos-collector" \
           ${container_id} /usr/local/bin/docker-entrypoint.sh "$@"

    if [ $? != 0 ] ; then
        die "Docker error"
    fi
}

fname=${releases_dir}/caos_collector-$(CI_PROJECT_DIR=. CI_COMMIT_SHA=${GIT_SHA} ci-tools/git-semver-pbr.sh)-py2-none-any.whl
if [ ! -f ${fname} ] ; then
    die "File ${fname} not found"
fi

docker_exec apk add --no-cache bash git

docker_exec git clone --no-checkout --no-hardlinks /origin /build
docker_exec git checkout -f ${GIT_SHA}

docker cp ${fname} ${container_id}:/build/

docker_exec ci-tools/docker-build.sh

docker stop ${container_id}
say "Stopped container: %s\n" ${container_id}

docker rm ${container_id}
say "Removed container: %s\n" ${container_id}

docker stop ${dind_container_id}
say "Stopped container: %s\n" ${dind_container_id}

docker rm ${dind_container_id}
say "Removed container: %s\n" ${dind_container_id}
