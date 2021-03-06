#!/usr/bin/python
#
# AbstractPatching is the base patching class of all the linux distros
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

class AbstractProvision(object):
    def __init__(self, hutil):
        self.mysql_user = "root"
        self.mysql_password = "root"
        self.http_root = "/var/www/"

    def install(self, software_list):
        if 'lamp' in software_list:
            self.install_lamp()
            others = software_list['lamp'].split(' ')
            for software in others:
                if hasattr(self, 'install_' + software):
                    getattr(self, 'install_' + software)()
        if 'lnmp' in software_list:
            self.install_lnmp()
            others = software_list['lnmp'].split(' ')
            for software in others:
                if hasattr(self, 'install_' + software):
                    getattr(self, 'install_' + software)()
        if 'javaenv' in software_list:
            self.install_javaenv()

    def install_wordpress(self):
        if not os.path.isdir("/azuredata"):
            os.mkdir("/azuredata")
        waagent.Run("mkdir /azuredata")
        waagent.Run("cd /azuredata && wget -c --no-check-certificate http://wordpress.org/latest.tar.gz")
        waagent.Run("cd /azuredata && tar xvzf latest.tar.gz")
        waagent.Run("mysqladmin -u" + self.mysql_user + " -p" + self.mysql_password + " create wordpress")

        with open("/azuredata/wordpress/wp-config-sample.php", "r") as f:
            wp_config = f.read()
        wp_config = wp_config.split('\n')
        wp_config[wp_config.index("define('DB_NAME', 'database_name_here');")] = "define('DB_NAME', 'wordpress');"
        wp_config[wp_config.index("define('DB_USER', 'username_here');")] = "define('DB_USER', '" + self.mysql_user + "');"
        wp_config[wp_config.index("define('DB_PASSWORD', 'password_here');")] = "define('DB_PASSWORD', '" + self.mysql_password + "');"
        with open("/azuredata/wordpress/wp-config.php", "w") as f:
            f.write('\n'.join(wp_config))

        waagent.Run("mv /azuredata/wordpress " + self.http_root)
        
    def install_phpwind(self):
        if not os.path.isdir("/azuredata"):
            os.mkdir("/azuredata")
        waagent.Run("cd /azuredata && wget -c --no-check-certificate http://www.phpwind.com/downloads/forums/phpwind_v9.0_utf8.zip")
        waagent.Run("cd /azuredata && unzip phpwind_v9.0_utf8")
        waagent.Run("mysqladmin -u" + self.mysql_user + " -p" + self.mysql_password + " create phpwind")
        authority = ["attachment", "conf", "data", "html", "src/extensions", "themes", "themes/*", "windid/attachment/"]
        waagent.Run("cd /azuredata/phpwind_v9.0_utf8/upload && chmod a+w " + ' '.join(authority))
        waagent.Run("mv /azuredata/phpwind_v9.0_utf8/upload " + self.http_root + "phpwind")
        waagent.Run("rm -r /azuredata/phpwind_v9.0_utf8")

    def install_discuz(self):
        if not os.path.isdir("/azuredata"):
            os.mkdir("/azuredata")
        waagent.Run("cd /azuredata && wget -c --no-check-certificate http://download.comsenz.com/DiscuzX/3.2/Discuz_X3.2_SC_UTF8.zip")
        waagent.Run("cd /azuredata && unzip Discuz_X3.2_SC_UTF8.zip")
        waagent.Run("mysqladmin -u" + self.mysql_user + " -p" + self.mysql_password + " create discuz")
        authority = ["config", "data", "uc_client", "uc_server"]
        waagent.Run("cd /azuredata/upload && chmod a+w -R " + ' '.join(authority))
        waagent.Run("mv /azuredata/upload " + self.http_root + "discuz")
        waagent.Run("rm -r /azuredata/readme")
        waagent.Run("rm -r /azuredata/utility")
        
    def install_phpMyAdmin(self):
        if not os.path.isdir("/azuredata"):
            os.mkdir("/azuredata")
        waagent.Run("cd /azuredata && wget -c --no-check-certificate http://jaist.dl.sourceforge.net/project/phpmyadmin/phpMyAdmin/4.2.8.1/phpMyAdmin-4.2.8.1-all-languages.zip")
        waagent.Run("cd /azuredata && unzip phpMyAdmin-4.2.8.1-all-languages.zip")
        waagent.Run("mv /azuredata/phpMyAdmin-4.2.8.1-all-languages " + self.http_root + "phpMyAdmin")

