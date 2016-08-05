#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: utils.py
# Created: 2016-07-19T12:48:44+0200
# Time-stamp: <2016-08-05T14:46:58cest>
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

def integrate(x, y):
    return numpy.trapz(x=x, y=y)


### Flat dict
# Taken from http://stackoverflow.com/questions/6027558/flatten-nested-python-dictionaries-compressing-keys

# >>> testData = {
#     'a':1,
#     'b':2,
#     'c':{
#         'aa':11,
#         'bb':22,
#         'cc':{
#             'aaa':111
#         }
#     }
# }
# from pprint import pprint as pp
#
# >>> pp(dict( flattenDict(testData, lift=lambda x:(x,)) ))
# {('a',): 1,
#  ('b',): 2,
#  ('c', 'aa'): 11,
#  ('c', 'bb'): 22,
#  ('c', 'cc', 'aaa'): 111}
#
# >>> pp(dict( flattenDict(testData, join=lambda a,b:a+'_'+b) ))
# {'a': 1, 'b': 2, 'c_aa': 11, 'c_bb': 22, 'c_cc_aaa': 111}
#
# >>> pp(dict( (v,k) for k,v in flattenDict(testData, lift=hash, join=lambda a,b:hash((a,b))) ))
# {1: 12416037344,
#  2: 12544037731,
#  11: 5470935132935744593,
#  22: 4885734186131977315,
#  111: 3461911260025554326}

from collections import Mapping
from itertools import chain
from operator import add

_FLAG_FIRST = object()

def flattenDict(d, join=add, lift=lambda x:x):
    results = []
    def visit(subdict, results, partialKey):
        for k,v in subdict.items():
            newKey = lift(k) if partialKey==_FLAG_FIRST else join(partialKey,lift(k))
            if isinstance(v,Mapping):
                visit(v, results, newKey)
            else:
                results.append((newKey,v))
    visit(d, results, _FLAG_FIRST)
    return results
