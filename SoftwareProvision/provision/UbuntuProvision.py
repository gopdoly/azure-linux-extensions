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
        waagent.Run("apt-get update")
        waagent.Run("apt-get install unzip")

    def install_lamp(self):
        waagent.Run("export DEBIAN_FRONTEND=noninteractive && apt-get -y install mysql-server mysql-client")
        waagent.Run("export DEBIAN_FRONTEND=noninteractive && apt-get -y install lamp-server^")

        with open('/etc/apache2/sites-available/' + os.listdir('/etc/apache2/sites-available')[0]) as f:
            conf = f.read()
        for line in conf.split('\n'):
            if line.strip().startswith('DocumentRoot '):
                self.http_root = line.split(' ')[1] + '/'
                break

        with open(self.http_root + "info.php", "w") as f:
            f.write("<?php\nphpinfo();\n?>")
        waagent.Run("mysqladmin -u root password " + self.mysql_password)

    def install_lnmp(self):
        waagent.Run("apt-get -y install nginx")
        waagent.Run("/etc/init.d/nginx start")

        waagent.Run("export DEBIAN_FRONTEND=noninteractive && apt-get -y install mysql-server mysql-client")
        waagent.Run("mysqladmin -u root password " + self.mysql_password)

        waagent.Run("apt-get -y install php5-fpm")
        waagent.Run("apt-get -y install php5-cli php5-cgi php5-mcrypt php5-mysql")

        # config lnmp
        try:
            with open("/etc/nginx/sites-available/default") as f:
                conf = f.read()
            conf = conf.split('\n')
            conf_strip = [s.strip() for s in conf]
            for i in range(0, len(conf)):
                if conf[i].strip().startswith("index ") and not "index.php" in conf[i]:
                    conf[i] = conf[i][:-1] + " index.php;"
            start = conf_strip.index(r"#location ~ \.php$ {")
            end = conf_strip[start:].index("#}") + start
            for i in range(start, end + 1):
                if '#' in conf[i]:
                    pos = conf[i].index('#')
                    conf[i] = conf[i][:pos] + conf[i][pos+1:]
                if conf[i].strip().startswith("fastcgi_pass 127.0.0.1"):
                    conf[i] = '#' + conf[i] 
            with open("/etc/nginx/sites-available/default", "w") as f:
                f.write('\n'.join(conf))
        except StandardError, e:
            print "config lnmp failed"
    
        for line in conf_strip:
            if line.startswith("root"):
                self.http_root = line.split(' ')[1].strip(';') + '/'
                break
        with open(self.http_root + "info.php", "w") as f:
            f.write("<?php\nphpinfo();\n?>")

        waagent.Run("/etc/init.d/nginx restart")
 
    def install_javaenv(self):
        waagent.Run("apt-get -y install openjdk-7-jdk")
        java_home = "/usr/lib/jvm/java-7-openjdk"
        for dir in os.listdir("/usr/lib/jvm/"):
            if dir.startswith("java-7-openjdk"):
                java_home = "/usr/lib/jvm/" + dir
                break
        with open("/etc/profile", "a") as f:
            f.write("\nexport JAVA_HOME=" + java_home + '\n')
            f.write("export CLASSPATH=.:${JAVA_HOME}/lib\n")
            f.write("export PATH=${JAVA_HOME}/bin:$PATH\n")
        waagent.Run("source /etc/profile")

        waagent.Run("apt-get -y install tomcat7")

        waagent.Run("export DEBIAN_FRONTEND=noninteractive && apt-get -y install mysql-server mysql-client")
        waagent.Run("mysqladmin -u root password " + self.mysql_password)

if __name__ == '__main__':
    a = UbuntuProvision(None)
#    a.install_javaenv()
    a.install_lnmp()
    a.install_discuz()
#    a.install_lamp()
#    a.install_wordpress()
#    a.install_phpwind()
