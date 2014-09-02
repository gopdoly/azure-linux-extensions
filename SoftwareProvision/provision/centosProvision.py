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
import sys
import imp
import base64
import re
import json
import platform
import shutil
import time
import traceback
import datetime

from Utils.WAAgentUtil import waagent
import Utils.HandlerUtil as Util

class centosProvision(AbstractProvision):
    def install_lamp(self):
        os.system("yum -y install httpd")
        os.system("chkconfig httpd on")
        os.system("/etc/init.d/httpd start")

        os.system("yum -y install mysql mysql-server")
        os.system("chkconfig mysqld on")
        os.system("/etc/init.d/mysqld start")

        os.system("yum -y install php php-mysql")
        os.system("/etc/init.d/httpd restart")
        with open("/var/www/html/info.php", "w") as f:
            f.write("<?php\nphpinfo();\n?>")
        
if __name__ == '__main__':
    a = centosConfigure()
    a.install_lamp()
        
