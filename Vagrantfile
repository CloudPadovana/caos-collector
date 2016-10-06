#!/usr/bin/env ruby
# encoding: utf-8

######################################################################
#
# Filename: Vagrantfile
# Created: 2016-10-06T11:03:53+0200
# Time-stamp: <2016-10-06T15:12:09cest>
# Author: Fabrizio Chiarello <fabrizio.chiarello@pd.infn.it>
#
# Copyright © 2016 by Fabrizio Chiarello
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
######################################################################

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
yum install -v -y python-devel python-pip
pip install --upgrade pip
SCRIPT

  config.vm.provision :shell, :inline => $script
end
