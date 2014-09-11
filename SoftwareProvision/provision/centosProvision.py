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
        os.system("yum -y install php-gd php-xml php-mbstring php-ldap php-pear php-xmlrpc")
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

        #set mysql password
        os.system("mysqladmin -u root password " + self.mysql_password)

        #config iptables
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
        os.system("service iptables restart")

    def install_lnmp(self):
        # install a third-party source
        if not os.path.isdir("/azuredata"):
            os.mkdir("/azuredata")
        os.system("cd /azuredata && wget http://www.atomicorp.com/installers/atomic")
        with open("/azuredata/atomic") as f:
            content = f.read()
        content = content.split('\n')
        content = [line.replace('read INPUTTEXT < /dev/tty', 'INPUTTEXT=yes') for line in content]
        with open("/azuredata/atomic", "w") as f:
            f.write('\n'.join(content))
        os.system("sh /azuredata/atomic")

        # install lnmp
        os.system("yum -y install nginx")
        os.system("chkconfig nginx on")
        os.system("service nginx start")

        os.system("yum -y install mysql mysql-server")
        os.system("chkconfig mysqld on")
        os.system("/etc/init.d/mysqld start")

        os.system("yum -y install php-fpm php-cli phh-cgi php-mcrypt php-mysql")
        os.system("chkconfig php-fpm on")
        os.system("service php-fpm start")

        # config nginx
        with open("/etc/nginx/conf.d/default.conf") as f:
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
                conf[i] = "fastcgi_param SCRIPT_FILENAME  $document_root$fastcgi_script_name;"
        with open("/etc/nginx/conf.d/default.conf", "w") as f:
            f.write('\n'.join(conf))

        for line in conf_strip:
            if line.startswith("root"):
                self.http_root = line.split(' ')[-1].strip(';') + '/'
                break
        with open(self.http_root + "info.php", "w") as f:
            f.write("<?php\nphpinfo();\n?>")

        os.system("service nginx restart")

        #config iptables
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
        os.system("service iptables restart")

    def install_javaenv(self):
        os.system("yum -y install java")
        java_home = "/usr/lib/jvm/jre-1.7.0-openjdk"
        with open("/etc/profile", "a") as f:
            f.write("\nexport JAVA_HOME=" + java_home + '\n')
            f.write("export JRE_HOME=${JAVA_HOME}/jre\n")
            f.write("export CLASSPATH=.:${JAVA_HOME}/lib:${JRE_HOME}/lib\n")
            f.write("export PATH=${JAVA_HOME}/bin:${JRE_HOME}/bin:$PATH\n")
        os.system("source /etc/profile")

        #install tomcat
        if not os.path.isdir("/azuredata"):
            os.mkdir("/azuredata")
        os.system("cd /azuredata && wget -c https://chiy.blob.core.windows.net/softwareprovision/apache-tomcat-7.0.55.tar.gz")
        os.system("cd /azuredata && tar xvzf apache-tomcat-7.0.55.tar.gz")
        os.system("cd /azuredata && mv apache-tomcat-7.0.55 tomcat")
        os.system("cd /azuredata/tomcat/bin && ./startup.sh")

        #isntall mysql
        os.system("yum -y install mysql mysql-server")
        os.system("chkconfig mysqld on")
        os.system("/etc/init.d/mysqld start")
        
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
        os.system("service iptables restart")

    def install_wordpress(self):
        super(centosProvision, self).install_wordpress()
        # set authority
        os.system("chcon -R -h -t httpd_sys_content_t " + self.http_root + 'wordpress/')
        os.system("/etc/init.d/httpd restart")

    def install_phpwind(self):
        super(centosProvision, self).install_phpwind()
        # set authority
        os.system("chcon -R -h -t httpd_sys_content_t " + self.http_root + 'phpwind/')
        os.system("/etc/init.d/httpd restart")
 
if __name__ == '__main__':
    a = centosProvision(None)
    a.install_javaenv()
 
