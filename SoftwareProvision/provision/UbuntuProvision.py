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

class UbuntuProvision(AbstractProvision):
    def __init__(self, hutil):
        super(UbuntuProvision, self).__init__(hutil)
        os.system("apt-get update")
        os.system("apt-get install unzip")

    def install_lamp(self):
        os.system("export DEBIAN_FRONTEND=noninteractive && apt-get -y install lamp-server^")
        with open(self.http_root + "info.php", "w") as f:
            f.write("<?php\nphpinfo();\n?>")
        with open('/etc/apache2/sites-available/' + os.listdir('/etc/apache2/sites-available')[0]) as f:
            conf = f.read()
        for line in conf.split('\n'):
            if line.strip().startswith('DocumentRoot '):
                self.http_root = line.split(' ')[1] + '/'
                break
                
        os.system("mysqladmin -u root password " + self.mysql_password)

    def install_lnmp(self):
        os.system("apt-get -y install nginx")
        os.system("/etc/init.d/nginx start")

        os.system("export DEBIAN_FRONTEND=noninteractive && apt-get -y install mysql-server mysql-client")
        os.system("mysqladmin -u root password " + self.mysql_password)

        os.system("apt-get -y install php5-cli php5-cgi php5-fpm php5-mcrypt php5-mysql")
        os.system("/etc/init.d/nginx restart")

    def install_javaenv(self):
        os.system("apt-get -y install openjdk-7-jdk")
        java_home = "/usr/lib/jvm/java-7-openjdk"
        for dir in os.listdir("/usr/lib/jvm/"):
            if dir.startswith("java-7-openjdk"):
                java_home = "/usr/lib/jvm/" + dir
                break
        with open("/root/.bashrc", "a") as f:
            f.write("\nexport JAVA_HOME=" + java_home + '\n')
            f.write("export CLASSPATH=.:${JAVA_HOME}/lib\n")
            f.write("export PATH=${JAVA_HOME}/bin:$PATH\n")
        os.system("bash")

        os.system("apt-get -y install tomcat7")

if __name__ == '__main__':
    a = UbuntuProvision(None)
#    a.install_lamp()
#    a.install_lnmp()
#    a.install_wordpress()
#    a.install_phpwind()
