#!/usr/bin/env ruby
# encoding: utf-8

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

VAGRANTFILE_API_VERSION = "2"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.define "caos-collector", primary: true do |collector|
    collector.vm.hostname = "caos-collector"
    collector.ssh.username = "vagrant"
    collector.ssh.password = "vagrant"

    collector.vm.provider :docker do |d|
      d.name = "caos-collector"
      d.has_ssh = true
      d.build_dir = "."
      d.dockerfile = "Dockerfile.vagrant"
      d.build_args = [ "-t", "vagrant-caos-collector" ]
    end

    $script = <<~SCRIPT
      DEBIAN_FRONTEND=noninteractive apt-get update && \
        apt-get install --no-install-recommends -y \
          python2.7 \
          python2.7-dev \
          python-pip \
          ipython

      pip install --upgrade pip
      pip install tox
    SCRIPT

    collector.vm.provision :shell, privileged: true, inline: $script
  end
end
