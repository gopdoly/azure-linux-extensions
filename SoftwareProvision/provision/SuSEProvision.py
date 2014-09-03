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
    def install_lamp(self):
        os.system("zypper -n in apache2")
        os.system("systemctl start apache2.service")
        os.system("systemctl enable apache2.service")
        os.system("chkconfig apache2 on")
        
        os.system("zypper -n in mysql mysql-client")
        os.system("chkconfig mysql on")
        os.system("service mysql start")
        
        os.system("zypper -n in php5 php5-mysql apache2-mod_php5")
        os.system("a2enmod php5")
        os.system("service apache2 restart")

        with open("/srv/www/htdocs/index.html", "w") as f:
            f.write("<html><body><h1>It works!</h1></body></html>")
        with open("/srv/www/htdocs/info.php", "w") as f:
            f.write("<?php\nphpinfo();\n?>")
                
if __name__ == '__main__':
    a = SuSEProvision(None)
    a.install_lamp()
