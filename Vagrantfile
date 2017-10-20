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

# disable parallel spawing of containers, otherwise 'vagrant up' will
# fail due to docker linking order
ENV['VAGRANT_NO_PARALLEL'] = 'yes'

CAOS_DB_NAME = "caos"
CAOS_DB_USERNAME = "caos"
CAOS_DB_PASSWORD = "CAOS_PASS"
CAOS_USERNAME = "admin"
CAOS_PASSWORD = "ADMIN_PASS"

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.define "caos-tsdb-db" do |db|
    db.vm.hostname = "caos-collector-tsdb-db"
    db.vm.synced_folder ".", "/vagrant", disabled: true

    db.vm.provider :docker do |d|
      d.name = "caos-collector-tsdb-db"
      d.has_ssh = false
      d.image = "mysql/mysql-server:5.7"
      d.create_args = [
        "-e", "MYSQL_ALLOW_EMPTY_PASSWORD=yes",
        "-e", "MYSQL_ROOT_HOST=172.17.0.%",
        "-e", "MYSQL_DATABASE=#{CAOS_DB_NAME}",
        "-e", "MYSQL_USER=#{CAOS_DB_USERNAME}",
        "-e", "MYSQL_PASSWORD=#{CAOS_DB_PASSWORD}",
      ]
    end
  end

  config.vm.define "caos-tsdb" do |tsdb|
    tsdb.vm.hostname = "caos-collector-tsdb"
    tsdb.vm.synced_folder ".", "/vagrant", disabled: true

    tsdb.vm.provider :docker do |d|
      d.name = "caos-collector-tsdb"
      d.has_ssh = false
      d.image = "baltig.infn.it:4567/chiarello/caos-tsdb:v0.1.3"
      d.create_args = [
        "-e", "CAOS_TSDB_DB_HOSTNAME=db",
        "-e", "CAOS_TSDB_DB_NAME=#{CAOS_DB_NAME}",
        "-e", "CAOS_TSDB_DB_USERNAME=#{CAOS_DB_USERNAME}",
        "-e", "CAOS_TSDB_DB_PASSWORD=#{CAOS_DB_PASSWORD}",
        "-e", "CAOS_TSDB_DB_POOL_SIZE=1",
        "-e", "CAOS_TSDB_PORT=4000",
        "-e", "CAOS_TSDB_AUTH_IDENTITY_USERNAME=#{CAOS_USERNAME}",
        "-e", "CAOS_TSDB_AUTH_IDENTITY_PASSWORD=#{CAOS_PASSWORD}",
        "--entrypoint", "/bin/bash",
      ]
      d.link "caos-collector-tsdb-db:db"
      d.cmd = [
        "-c", "bin/caos_tsdb migrate && bin/caos_tsdb dbcheck && bin/caos_tsdb foreground"
      ]
    end
  end

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
      d.create_args = [
        "-e", "CAOS_COLLECTOR_TSDB_API_URL=http://tsdb:4000/api/v1",
        "-e", "CAOS_COLLECTOR_TSDB_USERNAME=#{CAOS_USERNAME}",
        "-e", "CAOS_COLLECTOR_TSDB_PASSWORD=#{CAOS_PASSWORD}",
      ]
      d.link "caos-collector-tsdb:tsdb"
    end

    $script = <<~SCRIPT
      DEBIAN_FRONTEND=noninteractive apt-get update && \
        apt-get install --no-install-recommends -y \
          python2.7 \
          python2.7-dev \
          python-pip \
          ipython

      pip install --upgrade pip wheel setuptools
      pip install tox
    SCRIPT

    collector.vm.provision :shell, privileged: true, inline: $script
  end
end
