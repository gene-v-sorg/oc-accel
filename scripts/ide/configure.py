#!/usr/bin/env python
#
# Copyright 2019 International Business Machines
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

import os
import re
import os.path
import sys
from os.path import isdir as isdir
from os.path import isfile as isfile
from os.path import join as pathjoin
from shutil import copyfile
from ocaccel_utils import source
from ocaccel_utils import run_to_stdout
from ocaccel_utils import run_and_wait
from ocaccel_utils import msg
from ocaccel_utils import sed_file
from ocaccel_utils import search_file_group_1
from ocaccel_utils import append_file

class Configuration:
    def __init__(self, options):
        self.ocaccel_env_file = pathjoin(options.ocaccel_root, "ocaccel_env.sh")
        self.ocaccel_cfg_file = pathjoin(options.ocaccel_root, ".ocaccel_config")
        self.ocaccel_cfg_file_sh = pathjoin(options.ocaccel_root, ".ocaccel_config.sh")
        self.ocaccel_cfg_file_cflags = pathjoin(options.ocaccel_root, ".ocaccel_config.cflags")
        self.ocaccel_root = options.ocaccel_root
        self.ocse_path = options.ocse_path
        self.action_root = options.action_root
        self.simulator = options.simulator
        self.options = options
        self.log = None

    def cfg_existence(self):
        return isfile(self.ocaccel_env_file) and isfile(self.ocaccel_cfg_file)

    def setup_ocaccel_env(self):
        sed_file(self.ocaccel_env_file, '\${OCACCEL_ROOT}', self.ocaccel_root)
        sed_file(self.ocaccel_env_file, '\$OCACCEL_ROOT', self.ocaccel_root)

        if self.action_root is not None:
            sed_file(self.ocaccel_env_file, 'ACTION_ROOT\s*=\s*(.*)', 'ACTION_ROOT=' + self.action_root)

    def setup_cfg(self):
        if self.ocse_path is not None:
            ocse_line = 'OCSE_PATH="%s"' % self.ocse_path
            if isfile(self.ocaccel_cfg_file):
                sed_file(self.ocaccel_cfg_file, "\s*OCSE_PATH\s*=.*", ocse_line)
            else:
                append_file(self.ocaccel_cfg_file, ocse_line)
 
        if self.simulator is not None:
            simulator_line = ""
            if self.simulator.lower() == "xsim":
                simulator_line = "SIM_XSIM=y"
            elif self.simulator.lower() == "xcelium":
                simulator_line = "SIM_XCELIUM=y"
            elif self.simulator.lower() == "nosim":
                simulator_line = "NO_SIM=y"
            else:
                msg.fail_msg("%s is unknown simulator! Exiting ... " % self.simulator)
    
            if isfile(self.ocaccel_cfg_file):
                sed_file(self.ocaccel_cfg_file, r"^\s*(SIM_.*)\s*=.*", r"# \1 is not set")
                sed_file(self.ocaccel_cfg_file, "\s*NO_SIM\s*=.*", "# NO_SIM is not set")

                if simulator_line == "SIM_XSIM=y":
                    sed_file(self.ocaccel_cfg_file, "# SIM_XSIM is not set", simulator_line)
                elif simulator_line == "SIM_XCELIUM=y":
                    sed_file(self.ocaccel_cfg_file, "# SIM_XCELIUM is not set", simulator_line)
                elif simulator_line == "NO_SIM=y":
                    sed_file(self.ocaccel_cfg_file, "# NO_SIM is not set", simulator_line)
            else:
                append_file(self.ocaccel_cfg_file, simulator_line)

            sed_file(self.ocaccel_cfg_file, '\s*SIMULATOR\s*=\s*".*"\s*$', 'SIMULATOR="%s"' % self.simulator.lower())
    
        if isfile(self.ocaccel_env_file):
            sed_file(self.ocaccel_env_file, "^.*ocse_path\s*=.*", "", remove_matched_line = True)
    
    def update_cfg(self):
        if isfile(self.ocaccel_cfg_file):
            source(self.ocaccel_cfg_file)
            self.simulator = search_file_group_1(self.ocaccel_cfg_file, 'SIMULATOR\s*=\s*"(.*)"')
            self.ocse_path = os.path.expanduser(search_file_group_1(self.ocaccel_cfg_file, 'OCSE_PATH\s*=\s*"(.*)"'))

            if self.ocse_path is not None:
                sed_file(self.ocaccel_cfg_file,        "\s*OCSE_PATH\s*=.*",          "OCSE_PATH=\""          + os.path.abspath(self.ocse_path) + "\"")
                sed_file(self.ocaccel_cfg_file_sh,     "\s*export\s*OCSE_PATH\s*=.*",          "export OCSE_PATH="          + os.path.abspath(self.ocse_path) + "")
                sed_file(self.ocaccel_cfg_file_cflags, "\"\s*-DCONFIG_OCSE_PATH\s*=.*\"", "\"-DCONFIG_OCSE_PATH=" + os.path.abspath(self.ocse_path) + "\"")
        else:
            self.simulator = "nosim"
            self.ocse_path = os.path.abspath("../ocse")

        self.options.simulator = self.simulator
        self.options.ocse_path = os.path.abspath(self.ocse_path)
 
    def print_cfg(self):
        if isfile(self.ocaccel_env_file):
            msg.header_msg("\t%s\t%s" % ("ACTION_ROOT", search_file_group_1(self.ocaccel_env_file, 'ACTION_ROOT\s*=\s*(.*)')))
    
        if isfile(self.ocaccel_cfg_file):
            msg.header_msg("\t%s\t%s" % ("ACTION_NAME" , search_file_group_1(self.ocaccel_cfg_file , 'ACTION_NAME\s*=\s*"(.*)"')))
            msg.header_msg("\t%s\t%s" % ("FPGACARD"    , search_file_group_1(self.ocaccel_cfg_file , 'FPGACARD\s*=\s*"(.*)"')))
            msg.header_msg("\t%s\t%s" % ("FPGACHIP"    , search_file_group_1(self.ocaccel_cfg_file , 'FPGACHIP\s*=\s*"(.*)"')))
            msg.header_msg("\t%s\t%s" % ("SIMULATOR"   , search_file_group_1(self.ocaccel_cfg_file , 'SIMULATOR\s*=\s*"(.*)"')))
            msg.header_msg("\t%s\t%s" % ("CAPI_VER"    , search_file_group_1(self.ocaccel_cfg_file , 'CAPI_VER\s*=\s*"(.*)"')))
            msg.header_msg("\t%s\t%s" % ("OCSE_PATH"   , search_file_group_1(self.ocaccel_cfg_file , 'OCSE_PATH\s*=\s*"(.*)"')))
    
    def make_config(self):
        if self.options.predefined_config is not None:
            run_and_wait(cmd = "make -s oldconfig", work_dir = ".", log = self.log)
            run_and_wait(cmd = "make -s ocaccel_env", work_dir = ".", log = self.log)
        else:
            rc = run_to_stdout(cmd = "make -s menuconfig", work_dir = ".")
            if rc == 0:
                rc = run_to_stdout(cmd = "make -s ocaccel_env ocaccel_env_parm=config", work_dir = ".")

            if rc != 0:
                msg.warn_msg("=====================================================================")
                msg.warn_msg("==== Failed to bringup the configuration window.                 ====")
                msg.warn_msg("==== Please check if libncurses5-dev is installed on your system.====")
                msg.warn_msg("==== Also check if 'https://github.com/guillon/kconfig' is       ====")
                msg.warn_msg("==== accessible from your system.                                ====")
                msg.fail_msg("================= Configuration FAILED! =============================");

    def configure(self):
        msg.ok_msg_blue("--------> Configuration") 
        os.environ['OCACCEL_ROOT'] = self.ocaccel_root
        
        if self.options.predefined_config is not None:
            defconf = pathjoin(self.options.ocaccel_root, 'defconfig', self.options.predefined_config)

            if not isfile(defconf):
                msg.fail_msg("%s is not a valid defconfig file" % defconf)

            copyfile(defconf, pathjoin(self.options.ocaccel_root, self.ocaccel_cfg_file))

        self.setup_cfg()
        self.make_config()
        self.setup_ocaccel_env()
        msg.ok_msg("OCACCEL Configured")

        msg.header_msg("You've got configuration like:")
        self.print_cfg()
    
