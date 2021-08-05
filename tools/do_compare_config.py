#!/usr/bin/env python

# This script is used to compare the configuration files in
# the working directory and the local repository directory

import os, sys, filecmp
import config_common as common
import do_update_local_repo as local_repo

# do all
if __name__ == '__main__':

  # check if the local repo with TN2 configuration is available
  local_repo.check_local_repo(common.TN2_CONFIG_REPO_DIR, common.TN2_CONFIG_REPO_URL)

  # report difference between generated and existing configuration files
  local_repo.report_diff_files(common.WRS_DOT_CONFIG_DIR, common.TN2_CONFIG_REPO_DIR)

