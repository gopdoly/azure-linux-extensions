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
    def __init__(self):
        super(SuSEProvision, self).__init__()
        os.system("zypper -n in wget")

    def install_lamp(self):
        os.system("zypper -n in apache2")
        os.system("systemctl start apache2.service")
        os.system("systemctl enable apache2.service")
        os.system("chkconfig apache2 on")
        
        os.system("zypper -n in mariadb mariadb-tools")
        os.system("chkconfig mysql on")
        os.system("service mysql start")
        
        os.system("zypper -n in php5 php5-mysql apache2-mod_php5")
        os.system("a2enmod php5")
        os.system("service apache2 restart")

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
        os.system("mysqladmin -u root password " + self.mysql_password)

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
            os.system("systemctl restart SuSEfirewall2.service")
        except StandardError, e:
            print "config firewall failed"
 
    def install_lnmp(self):
        os.system("zypper -n in nginx")
        os.system("systemctl start nginx.service")
        os.system("systemctl enable nginx.service")
        os.system("chkconfig nginx on")

        os.system("zypper -n in mariadb mariadb-tools")
        os.system("chkconfig mysql on")
        os.system("service mysql start")
        
        os.system("zypper -n in php5-fpm php5-mysql")
        os.system("cp /etc/php5/fpm/php-fpm.conf.default /etc/php5/fpm/php-fpm.conf")
        with open("/etc/php5/fpm/php-fpm.conf") as f:
            conf = f.read()
        conf = conf.split('\n')
        conf[conf.index(";error_log = log/php-fpm.log")] = "error_log = /var/log/php-fpm.log"
        with open("/etc/php5/fpm/php-fpm.conf", "w") as f:
            f.write('\n'.join(conf))
        os.system("php-fpm")
        os.system("systemctl start php-fpm.service")

        #set mysql password
        os.system("mysqladmin -u root password " + self.mysql_password)

        # config nginx
        with open("/etc/nginx/nginx.conf") as f:
            conf = f.read()
        conf = conf.split('\n')
        conf_strip = [s.strip() for s in conf]
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
        os.system("systemctl restart nginx.service")

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
            os.system("systemctl restart SuSEfirewall2.service")
        except StandardError, e:
            print "config firewall failed"
 
    def install_javaenv(self):
        os.system("zypper -n in java-1_7_0-openjdk")
        java_home = os.popen("find /usr -name java-1.7.0-openjdk | grep /jvm/").read()
        with open("/etc/profile", "a") as f:
            f.write("\nexport JAVA_HOME=" + java_home + '\n')
            f.write("export JRE_HOME=${JAVA_HOME}/jre\n")
            f.write("export CLASSPATH=.:${JAVA_HOME}/lib:${JRE_HOME}/lib\n")
            f.write("export PATH=${JAVA_HOME}/bin:${JRE_HOME}/bin:$PATH\n")
        os.system("source /etc/profile")

        #install tomcat
        if not os.path.isdir("/azuredata"):
            os.mkdir("/azuredata")
        os.system("cd /azuredata && wget -c --no-check-certificate https://chiy.blob.core.windows.net/softwareprovision/apache-tomcat-7.0.55.tar.gz")
        os.system("cd /azuredata && tar xvzf apache-tomcat-7.0.55.tar.gz")
        os.system("cd /azuredata && mv apache-tomcat-7.0.55 tomcat")
        os.system("cd /azuredata/tomcat/bin && ./startup.sh")

        # isntall mysql
        os.system("zypper -n in mariadb mariadb-tools")
        os.system("chkconfig mysql on")
        os.system("service mysql start")
        os.system("mysqladmin -u root password " + self.mysql_password)
 
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
            os.system("systemctl restart SuSEfirewall2.service")
        except StandardError, e:
            print "config firewall failed"
 
if __name__ == '__main__':
    a = SuSEProvision(None)
    a.install_javaenv()
