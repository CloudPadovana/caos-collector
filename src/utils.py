#!/usr/bin/env python
# -*- coding: utf-8 -*-

######################################################################
#
# Filename: utils.py
# Created: 2016-07-19T12:48:44+0200
# Time-stamp: <2016-07-21T17:23:54cest>
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

def format_date(date):
    return date.strftime("%Y-%m-%dT%H:%M:%SZ")

def parse_date(date):
    return datetime.datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")


### The following functions are adapted from numpy, and come with the
### following license.

# Copyright (c) 2005-2016, NumPy Developers.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     * Redistributions of source code must retain the above copyright
#        notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above
#        copyright notice, this list of conditions and the following
#        disclaimer in the documentation and/or other materials provided
#        with the distribution.
#
#     * Neither the name of the NumPy Developers nor the names of any
#        contributors may be used to endorse or promote products derived
#        from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# LICENSE.txt (END)

def binary_search(x, x0):
    L = len(x)

    # Handle keys outside of the arr range first
    if x0 > x[L-1]: return L
    elif x0 < x[0]: return -1

    imin = 0
    imax = L
    # finally, find index by bisection
    while imin < imax:
        imid = imin + ((imax - imin) >> 1)
        if x0 >= x[imid]: imin = imid + 1
        else: imax = imid
    return imin - 1

def interp(x, y, x0, left=None, right=None):
    L = len(x)

    if left is None: left = y[0]
    if right is None: right = y[L-1]

    j = binary_search(x, x0)
    if j == -1: return left
    elif j == L: return right
    elif j == L - 1: return dy[j]
    else:
        slope = (y[j+1] - y[j]) / (x[j+1] - x[j])
        return (slope*(x0 - x[j]) + y[j])
