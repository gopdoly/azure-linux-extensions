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
    def __init__(self, hutil):
        super(centosProvision, self).__init__(hutil)
        waagent.Run("yum -y install wget")
        waagent.Run("yum -y install unzip")

    def install_lamp(self):
        waagent.Run("yum -y install httpd")
        waagent.Run("chkconfig httpd on")
        waagent.Run("/etc/init.d/httpd start")

        waagent.Run("yum -y install mysql mysql-server")
        waagent.Run("chkconfig mysqld on")
        waagent.Run("/etc/init.d/mysqld start")

        waagent.Run("yum -y install php php-mysql")
        waagent.Run("yum -y install php-gd php-xml php-mbstring php-ldap php-pear php-xmlrpc")
        waagent.Run("/etc/init.d/httpd restart")

        #get http root
        with open("/etc/httpd/conf/httpd.conf") as f:
            conf = f.read()
        for line in conf.split('\n'):
            if line.strip().startswith('DocumentRoot '):
                self.http_root = line.split(' ')[1].strip('"') + '/'
                break
        with open(self.http_root + "info.php", "w") as f:
            f.write("<?php\nphpinfo();\n?>")

        #set mysql password
        waagent.Run("mysqladmin -u root password " + self.mysql_password)

        #config iptables
        try:
            with open("/etc/sysconfig/iptables") as f:
                conf = f.read()
            conf = conf.split('\n')
            for i in range(0, len(conf)):
                if conf[i].startswith(":OUTPUT ACCEPT"):
                    pos = i
                    break
            if not "-A INPUT -m state --state NEW -m tcp -p tcp --dport 3306 -j ACCEPT" in conf:
                conf.insert(pos, "-A INPUT -m state --state NEW -m tcp -p tcp --dport 3306 -j ACCEPT")
            if not "-A INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT" in conf:
                conf.insert(pos, "-A INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT")
            with open("/etc/sysconfig/iptables", "w") as f:
                f.write("\n".join(conf)) 
            waagent.Run("service iptables restart")
        except StandardError, e:
            print "config iptables failed"

    def install_lnmp(self):
        # install a third-party source
        if not os.path.isdir("/azuredata"):
            os.mkdir("/azuredata")
        waagent.Run("cd /azuredata && wget http://www.atomicorp.com/installers/atomic")
        with open("/azuredata/atomic") as f:
            content = f.read()
        content = content.split('\n')
        content = [line.replace('read INPUTTEXT < /dev/tty', 'INPUTTEXT=yes') for line in content]
        with open("/azuredata/atomic", "w") as f:
            f.write('\n'.join(content))
        waagent.Run("sh /azuredata/atomic")

        # install lnmp
        waagent.Run("yum -y install nginx")
        waagent.Run("chkconfig nginx on")
        waagent.Run("service nginx start")

        waagent.Run("yum -y install mysql mysql-server")
        waagent.Run("chkconfig mysqld on")
        waagent.Run("/etc/init.d/mysqld start")

        waagent.Run("yum -y install php-fpm php-cli phh-cgi php-mcrypt php-mysql")
        waagent.Run("chkconfig php-fpm on")
        waagent.Run("service php-fpm start")

        # set mysql password
        waagent.Run("mysqladmin -u root password " + self.mysql_password)

        # config nginx
        with open("/etc/nginx/conf.d/default.conf") as f:
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
                conf[i] = "fastcgi_param SCRIPT_FILENAME  $document_root$fastcgi_script_name;"
        with open("/etc/nginx/conf.d/default.conf", "w") as f:
            f.write('\n'.join(conf))

        for line in conf_strip:
            if line.startswith("root"):
                self.http_root = line.split(' ')[-1].strip(';') + '/'
                break
        with open(self.http_root + "info.php", "w") as f:
            f.write("<?php\nphpinfo();\n?>")

        waagent.Run("service nginx restart")

        #config iptables
        try:
            with open("/etc/sysconfig/iptables") as f:
                conf = f.read()
            conf = conf.split('\n')
            for i in range(0, len(conf)):
                if conf[i].startswith(":OUTPUT ACCEPT"):
                    pos = i
                    break
            if not "-A INPUT -m state --state NEW -m tcp -p tcp --dport 3306 -j ACCEPT" in conf:
                conf.insert(pos + 1, "-A INPUT -m state --state NEW -m tcp -p tcp --dport 3306 -j ACCEPT")
            if not "-A INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT" in conf:
                conf.insert(pos + 1, "-A INPUT -m state --state NEW -m tcp -p tcp --dport 80 -j ACCEPT")
            with open("/etc/sysconfig/iptables", "w") as f:
                f.write("\n".join(conf))
            waagent.Run("service iptables restart")
        except StandardError, e:
            print "config iptables failed"

    def install_javaenv(self):
        waagent.Run("yum -y install java")
        java_home = "/usr/lib/jvm/jre-1.7.0-openjdk"
        with open("/etc/profile", "a") as f:
            f.write("\nexport JAVA_HOME=" + java_home + '\n')
            f.write("export JRE_HOME=${JAVA_HOME}/jre\n")
            f.write("export CLASSPATH=.:${JAVA_HOME}/lib:${JRE_HOME}/lib\n")
            f.write("export PATH=${JAVA_HOME}/bin:${JRE_HOME}/bin:$PATH\n")
        waagent.Run("source /etc/profile")

        #install tomcat
        if not os.path.isdir("/azuredata"):
            os.mkdir("/azuredata")
        waagent.Run("cd /azuredata && wget -c https://chiy.blob.core.windows.net/softwareprovision/apache-tomcat-7.0.55.tar.gz")
        waagent.Run("cd /azuredata && tar xvzf apache-tomcat-7.0.55.tar.gz")
        waagent.Run("cd /azuredata && mv apache-tomcat-7.0.55 tomcat")
        waagent.Run("cd /azuredata/tomcat/bin && ./startup.sh")

        #isntall mysql
        waagent.Run("yum -y install mysql mysql-server")
        waagent.Run("chkconfig mysqld on")
        waagent.Run("/etc/init.d/mysqld start")
        waagent.Run("mysqladmin -u root password " + self.mysql_password)
       
        #config iptables
        with open("/etc/sysconfig/iptables") as f:
            conf = f.read()
        conf = conf.split('\n')
        for i in range(0, len(conf)):
            if conf[i].startswith(":OUTPUT ACCEPT"):
                pos = i
                break
        if not "-A INPUT -m state --state NEW -m tcp -p tcp --dport 8080 -j ACCEPT" in conf:
            conf.insert(pos + 1, "-A INPUT -m state --state NEW -m tcp -p tcp --dport 8080 -j ACCEPT")
        with open("/etc/sysconfig/iptables", "w") as f:
            f.write("\n".join(conf))
        waagent.Run("service iptables restart")

    def install_wordpress(self):
        super(centosProvision, self).install_wordpress()
        # set authority
        waagent.Run("chcon -R -h -t httpd_sys_content_t " + self.http_root + 'wordpress/')
        waagent.Run("/etc/init.d/httpd restart")

    def install_phpwind(self):
        super(centosProvision, self).install_phpwind()
        # set authority
        waagent.Run("chcon -R -h -t httpd_sys_content_t " + self.http_root + 'phpwind/')
        waagent.Run("/etc/init.d/httpd restart")
        
    def install_discuz(self):
        super(centosProvision, self).install_discuz()
        # set authority
        waagent.Run("chcon -R -h -t httpd_sys_content_t " + self.http_root + 'discuz/')
        waagent.Run("/etc/init.d/httpd restart")

    def install_phpMyAdmin(self):
        super(centosProvision, self).install_phpMyAdmin()
        # set authority
        waagent.Run("chcon -R -h -t httpd_sys_content_t " + self.http_root + 'phpMyAdmin/')
        waagent.Run("/etc/init.d/httpd restart")
 

if __name__ == '__main__':
    a = centosProvision(None)
    a.install_javaenv()
 
