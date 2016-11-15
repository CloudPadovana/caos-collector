#!/usr/bin/env ruby
# encoding: utf-8

################################################################################
#
# caos-collector - CAOS collector
#
# Copyright © 2016 INFN - Istituto Nazionale di Fisica Nucleare (Italy)
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
  config.vm.provider "virtualbox" do |v|
    v.memory = 512
    v.cpus = 1
    v.linked_clone = true
  end

  config.vm.box = "centos/7"

  config.vm.synced_folder ".", "/vagrant", type: "rsync",
                          rsync__exclude: [".git/", "venv/"],
                          rsync__auto: true,
                          rsync__verbose: true

  config.vm.hostname = "collector.caos.vagrant.localhost"

  $script = <<SCRIPT
sed -i 's/AcceptEnv/# AcceptEnv/' /etc/ssh/sshd_config
localectl set-locale "LANG=en_US.utf8"
systemctl reload sshd.service

echo "cd /vagrant" >> /home/vagrant/.bash_profile

yum update -v -y
yum install -v -y epel-release

### PYTHON
yum install -v -y python-devel python-pip python-virtualenv

su -c "virtualenv venv" - vagrant
su -c ". venv/bin/activate; pip install --upgrade pip" - vagrant
SCRIPT

  config.vm.provision :shell, :inline => $script
end
