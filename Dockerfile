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

FROM python:2.7

LABEL maintainer "Fabrizio Chiarello <fabrizio.chiarello@pd.infn.it>"

ARG RELEASE_FILE
ADD $RELEASE_FILE /

WORKDIR /

RUN pip install --no-cache-dir /$(basename ${RELEASE_FILE}) && \
    rm -f /$(basename ${RELEASE_FILE})

ENV LANG=C.UTF-8

VOLUME /etc/caos

RUN mkdir /var/log/caos
VOLUME /var/log/caos

ENTRYPOINT [ "caos_collector" ]
CMD [ "--help" ]
