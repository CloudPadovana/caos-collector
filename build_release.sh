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

SCRIPT=$(basename "$0")
USAGE="$SCRIPT [<options>]
  Options:
    -h, --help                          Show help information
    -t, --target <commit> | <tag>       The commit or the tag to be built. Defaults to HEAD."

function die() {
    format=${1:-""}
    shift
    printf >&2 "$format\n" "$@"
    exit 1
}

function say() {
    format=${1:-""}
    shift
    printf "${format}\n" "$@"
}

function show_usage() {
    echo "usage: ${USAGE}"
}

OPTS=$(getopt -o ht: -l help,target: -n ${SCRIPT} -- "$@")
if [ $? != 0 ] ; then
    show_usage
    die
fi
eval set -- "${OPTS}"

target=HEAD
while true ; do
    case "$1" in
        -h|--help)
            show_usage
            exit 0
            ;;
        -t|--target)
            target="$2"
            shift 2
            ;;
        --)
            shift
            ;;
        "")
            break
            ;;
        *)
            show_usage
            die "Unknown argument: %s" $1
            ;;
    esac
done

ret=$(git describe --long $target 2>&1)
if [ $? != 0 ] ; then
    die "Unable to find '%s' (git: '%s')" "${target}" "${ret}"
fi
git_version=$ret

function git_to_semver () {
    local git_version=$1
    local version=$(echo ${git_version} | awk '{ split($0, r, "-"); print r[1] }' | sed -e 's/^v//' )
    local count=$(echo ${git_version} | awk '{ split($0, r, "-"); print r[2] }' )
    local sha=$(echo ${git_version} | awk '{ split($0, r, "-"); print r[3] }' )

    if [ ${count} == 0 ] ; then
        echo "${version}"
    else
        echo "${version}.${count}+${sha}"
    fi
}

semver=$(git_to_semver ${git_version})
semver_pbr=$(echo "${semver}" | sed -e 's/+/./')

say "
Target:      ${target}
Git version: ${git_version}
Semver:      ${semver}
PBR Semver:  ${semver_pbr}
"

releases_dir=releases

wheel_fname="caos_collector-${semver_pbr}-py2-none-any.whl"
archive_fname="caos-collector-${semver}.tar.gz"

archive_prefix="caos-collector/"
git archive --prefix=${archive_prefix} -o ${releases_dir}/${archive_fname} ${git_version}
say "Created archive: %s\n" ${archive_fname}

container_id=$(docker run -t -d -v /${archive_prefix} -w /${archive_prefix} -v $(readlink -e ${releases_dir}/${archive_fname}):/${archive_fname}:ro --entrypoint /bin/bash python:2.7)
say "Started container: %s\n" ${container_id}

function docker_exec () {
    docker exec "$@"
    if [ $? != 0 ] ; then
        die "Docker error"
    fi
}

docker_exec ${container_id} tar xfz /${archive_fname} --strip-components=1
say "Deployed sources\n"

say "Starting compilation"
docker_exec -e "PBR_VERSION=${semver_pbr}" ${container_id} python setup.py bdist_wheel -v
say "Compilation done\n"

docker cp "${container_id}:/${archive_prefix}/dist/${wheel_fname}" ${releases_dir}/
say "Grabbed wheel %s to %s\n" ${wheel_fname} ${releases_dir}/

docker stop ${container_id}
say "Stopped container: %s\n" ${container_id}

docker rm ${container_id}
say "Removed container: %s\n" ${container_id}

say "Building docker release"
docker build -t caos-collector:${git_version} --build-arg WHEEL_FILE=${wheel_fname} --build-arg RELEASES_DIR=${releases_dir} .
say "Docker release built\n"
