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

class SuSEProvision(AbstractProvision):
    def __init__(self, hutil):
        super(SuSEProvision, self).__init__(hutil)
        waagent.Run("zypper -n in wget")

    def install_lamp(self):
        waagent.Run("zypper -n in apache2")
        waagent.Run("systemctl start apache2.service")
        waagent.Run("systemctl enable apache2.service")
        waagent.Run("chkconfig apache2 on")
        
        waagent.Run("zypper -n in mariadb mariadb-tools")
        waagent.Run("chkconfig mysql on")
        waagent.Run("service mysql start")
        
        waagent.Run("zypper -n in php5 php5-mysql apache2-mod_php5")
        waagent.Run("a2enmod php5")
        waagent.Run("service apache2 restart")

        # get http root
        with open("/etc/apache2/default-server.conf") as f:
            conf = f.read()
        for line in conf.split('\n'):
            if line.strip().startswith('DocumentRoot '):
                self.http_root = line.split(' ')[1].strip('"') + '/'
                break

        with open(self.http_root + "info.php", "w") as f:
            f.write("<?php\nphpinfo();\n?>")
        with open(self.http_root + "index.html", "w") as f:
            f.write("<html><body><h1>It works!</h1></body></html>")

        #set mysql password
        waagent.Run("mysqladmin -u root password " + self.mysql_password)

        # config firewall
        try:
            with open("/etc/sysconfig/SuSEfirewall2") as f:
                conf = f.read()
            conf = conf.split('\n')
            for i in range(0, len(conf)):
                if conf[i].startswith("FW_SERVICES_EXT_TCP"):
                    conf[i] = conf[i][:-1] + ' 80"'
                    break
            with open("/etc/sysconfig/SuSEfirewall2", "w") as f:
                f.write('\n'.join(conf))
            waagent.Run("systemctl restart SuSEfirewall2.service")
        except StandardError, e:
            print "config firewall failed"
 
    def install_lnmp(self):
        waagent.Run("zypper -n in nginx")
        waagent.Run("systemctl start nginx.service")
        waagent.Run("systemctl enable nginx.service")
        waagent.Run("chkconfig nginx on")

        waagent.Run("zypper -n in mariadb mariadb-tools")
        waagent.Run("chkconfig mysql on")
        waagent.Run("service mysql start")
        
        waagent.Run("zypper -n in php5-fpm php5-mysql")
        waagent.Run("cp /etc/php5/fpm/php-fpm.conf.default /etc/php5/fpm/php-fpm.conf")
        with open("/etc/php5/fpm/php-fpm.conf") as f:
            conf = f.read()
        conf = conf.split('\n')
        conf[conf.index(";error_log = log/php-fpm.log")] = "error_log = /var/log/php-fpm.log"
        with open("/etc/php5/fpm/php-fpm.conf", "w") as f:
            f.write('\n'.join(conf))
        waagent.Run("php-fpm")
        waagent.Run("systemctl start php-fpm.service")

        #set mysql password
        waagent.Run("mysqladmin -u root password " + self.mysql_password)

        # config nginx
        with open("/etc/nginx/nginx.conf") as f:
            conf = f.read()
        conf = conf.split('\n')
        conf_strip = [s.strip() for s in conf]
        for i in range(0, len(conf)):
            if conf[i].strip().startswith("index "):
                conf[i] = conf[i][:-1] + " index.php;"
        start = conf_strip.index(r"# pass the PHP scripts to FastCGI server listening on 127.0.0.1:9000")
        start = conf_strip[start:].index(r"#location ~ \.php$ {") + start
        end = conf_strip[start:].index(r"#}") + start
        for i in range(start, end + 1):
            if '#' in conf[i]:
                pos = conf[i].index('#')
                conf[i] = conf[i][:pos] + conf[i][pos+1:]
            if "fastcgi_param" in conf[i] and "SCRIPT_FILENAME" in conf[i]:
                conf[i] = "fastcgi_param SCRIPT_FILENAME  /srv/www/htdocs/$fastcgi_script_name;"
        with open("/etc/nginx/nginx.conf", "w") as f:
            f.write('\n'.join(conf))
        waagent.Run("systemctl restart nginx.service")

        for line in conf_strip:
            if line.startswith("root"):
                self.http_root = line.split(' ')[-1].strip(';') + '/'
                break
        with open(self.http_root + "index.html", "w") as f:
            f.write("<html><body><h1>It works!</h1></body></html>")
        with open(self.http_root + "info.php", "w") as f:
            f.write("<?php\nphpinfo();\n?>")

        # config firewall
        try:
            with open("/etc/sysconfig/SuSEfirewall2") as f:
                conf = f.read()
            conf = conf.split('\n')
            for i in range(0, len(conf)):
                if conf[i].startswith("FW_SERVICES_EXT_TCP"):
                    conf[i] = conf[i][:-1] + ' 80"'
                    break
            with open("/etc/sysconfig/SuSEfirewall2", "w") as f:
                f.write('\n'.join(conf))
            waagent.Run("systemctl restart SuSEfirewall2.service")
        except StandardError, e:
            print "config firewall failed"
 
    def install_javaenv(self):
        waagent.Run("zypper -n in java-1_7_0-openjdk")
        java_home = os.popen("find /usr -name java-1.7.0-openjdk | grep /jvm/").read()
        with open("/etc/profile", "a") as f:
            f.write("\nexport JAVA_HOME=" + java_home + '\n')
            f.write("export JRE_HOME=${JAVA_HOME}/jre\n")
            f.write("export CLASSPATH=.:${JAVA_HOME}/lib:${JRE_HOME}/lib\n")
            f.write("export PATH=${JAVA_HOME}/bin:${JRE_HOME}/bin:$PATH\n")
        waagent.Run("source /etc/profile")

        #install tomcat
        if not os.path.isdir("/azuredata"):
            os.mkdir("/azuredata")
        waagent.Run("cd /azuredata && wget -c --no-check-certificate https://chiy.blob.core.windows.net/softwareprovision/apache-tomcat-7.0.55.tar.gz")
        waagent.Run("cd /azuredata && tar xvzf apache-tomcat-7.0.55.tar.gz")
        waagent.Run("cd /azuredata && mv apache-tomcat-7.0.55 tomcat")
        waagent.Run("cd /azuredata/tomcat/bin && ./startup.sh")

        # isntall mysql
        waagent.Run("zypper -n in mariadb mariadb-tools")
        waagent.Run("chkconfig mysql on")
        waagent.Run("service mysql start")
        waagent.Run("mysqladmin -u root password " + self.mysql_password)
 
        # config firewall
        try:
            with open("/etc/sysconfig/SuSEfirewall2") as f:
                conf = f.read()
            conf = conf.split('\n')
            for i in range(0, len(conf)):
                if conf[i].startswith("FW_SERVICES_EXT_TCP"):
                    conf[i] = conf[i][:-1] + ' 8080"'
                    break
            with open("/etc/sysconfig/SuSEfirewall2", "w") as f:
                f.write('\n'.join(conf))
            waagent.Run("systemctl restart SuSEfirewall2.service")
        except StandardError, e:
            print "config firewall failed"
 
if __name__ == '__main__':
    a = SuSEProvision(None)
    a.install_lnmp()
    a.install_wordpress()
