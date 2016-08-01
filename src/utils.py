#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: utils.py
# Created: 2016-07-19T12:48:44+0200
# Time-stamp: <2016-08-01T10:01:59cest>
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

import datetime

import numpy

EPOCH = datetime.datetime(year=1970,
                          month=1,
                          day=1,
                          hour=0,
                          minute=0,
                          second=0,
                          microsecond=0,
                          tzinfo=None)

def format_date(date):
    return date.strftime("%Y-%m-%dT%H:%M:%SZ")

def parse_date(date):
    return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")

def interp(x, y, x0, left=None, right=None):
    # check order
    if not numpy.all(numpy.diff(x) > 0):
        # sort
        idxs = numpy.argsort(x)
        x = x[idxs]
        y = numpy.take(y, idxs)

    y0 = numpy.interp(x0, x, y, left=left, right=right)
    return y0
