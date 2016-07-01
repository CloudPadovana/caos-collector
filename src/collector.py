#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: collector.py
# Created: 2016-06-29T14:32:26+0200
# Time-stamp: <2016-07-01T12:38:58cest>
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

import argparse
import ConfigParser

from _version import __version__
from store import Store
import log

from pymongo import MongoClient


log.setup_logger()
logger = log.get_logger()
logger.info("Logger setup.")

# CLI ARGs
parser = argparse.ArgumentParser(description='Data collector for CAOS-NG.',
                                 add_help=True)

parser.add_argument('-v', '--version', action='version',
                    version='%(prog)s {version}'.format(version=__version__))

parser.add_argument('-c', '--config',
                    dest='cfg_file', metavar='FILE',
                    default='collector.conf',
                    help='configuration file')


def get_meter_db(db_connection):
    logger.info("Connecting to: %s." % db_connection)
    mongo = MongoClient(db_connection)
    logger.debug(mongo.server_info())

    db = mongo.ceilometer
    meter = db.meter
    return meter


def get_cfg_option(section, option):
    if not config.has_option(section, option):
        raise SystemError("No %(section)s/%(option)s option in '%(cfg_file)s'")
    return config.get(section, option)

config = ConfigParser.RawConfigParser()


def main():
    args = parser.parse_args()
    cfg_file = args.cfg_file
    logger.info("Reading configuration file: %s." % cfg_file)
    config.read(cfg_file)

    db_connection = get_cfg_option('db', 'connection')
    store_api_url = get_cfg_option('store', 'api-url')

    store = Store(store_api_url)
    projects = store.get('projects')
    meters = get_meter_db(db_connection)


if __name__ == "__main__":
    main()
