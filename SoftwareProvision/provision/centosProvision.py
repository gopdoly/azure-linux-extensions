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
from AbstractProvision import AbstractProvision

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

        #get http root
        with open("/etc/httpd/conf/httpd.conf") as f:
            conf = f.read()
        for line in conf.split('\n'):
            if line.strip().startswith('DocumentRoot '):
                self.http_root = line.split(' ')[1].strip('"') + '/'
                break
        with open(self.http_root + "info.php", "w") as f:
            f.write("<?php\nphpinfo();\n?>")

        #set authority
        os.system("chcon -R -h -t httpd_sys_content_t /var/www/html/")
        os.system("/etc/init.d/httpd restart")

        #set mysql password
        os.system("mysqladmin -u root password " + self.mysql_password)

        #config iptables
        with open("/etc/sysconfig/iptables") as f:
            conf = f.read()
        conf = conf.split('\n')
        pos = conf.index("-A INPUT -m state --state NEW -m tcp -p tcp --dport 22 -j ACCEPT")
        if not "-A INPUT -m state --state NEW -m tcp -p tcp --dport 3306 -j ACCEPT" in conf:
            conf.insert(pos + 1, "-A INPUT -m state --state NEW -m tcp -p tcp --dport 3306 -j ACCEPT")
        if not "-A INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT" in conf:
            conf.insert(pos + 1, "-A INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT")
        with open("/etc/sysconfig/iptables", "w") as f:
            f.write("\n".join(conf)) 
        os.system("service iptables restart")
        
if __name__ == '__main__':
    a = centosProvision(None)
    a.install_lamp()
 
