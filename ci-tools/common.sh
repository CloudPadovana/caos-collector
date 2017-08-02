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
