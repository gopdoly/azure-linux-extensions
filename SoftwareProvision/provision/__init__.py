#!/usr/bin/python
#
# Copyright 2014 Microsoft Corporation
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
# Requires Python 2.4+

import os
import re
import platform

from UbuntuProvision import UbuntuProvision
from centosProvision import centosProvision

# Define the function in case waagent(<2.0.4) doesn't have DistInfo()
def DistInfo(fullname=0):
    if 'FreeBSD' in platform.system():
        release = re.sub('\-.*\Z', '', str(platform.release()))
        distinfo = ['FreeBSD', release]
        return distinfo
    if os.path.isfile('/etc/oracle-release'):
        release = re.sub('\-.*\Z', '', str(platform.release()))
        distinfo = ['Oracle', release]
        return distinfo
    if 'linux_distribution' in dir(platform):
        distinfo = list(platform.linux_distribution(\
                        full_distribution_name=fullname))
        # remove trailing whitespace in distro name
        distinfo[0] = distinfo[0].strip()
        return distinfo
    else:
        return platform.dist()

def GetMyProvision(hutil, provision_class_name=''):
    """
    Return MyProvision object.
    NOTE: Logging is not initialized at this point.
    """
    if provision_class_name == '':
        if 'Linux' in platform.system():
            Distro = DistInfo()[0]
        else:
            if 'FreeBSD' in platform.system():
                Distro = platform.system()
        Distro = Distro.strip('"')
        Distro = Distro.strip(' ')
        provision_class_name = Distro + 'Provision'
    else:
        Distro = provision_class_name
    if not globals().has_key(provision_class_name):
        print Distro+' is not a supported distribution.'
        return None
    return globals()[provision_class_name](hutil)
