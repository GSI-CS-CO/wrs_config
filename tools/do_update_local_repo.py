#!/usr/bin/env python

# This script is used to update the local repo directory with
# the generated configuration files.

import os, sys, glob, subprocess, shutil, filecmp
import config_common as common

# check if the output working directory is available
def check_output_dir(working_dir):

  if not os.path.exists(working_dir):
    print ('? Info: comparison is impossible! The output working directory %s is not found!' % working_dir)
    print ('Possible causes: the output directory was cleaned; configuration was not generated.\n')
    sys.exit(1)

# check if the local repo with TN2 configuration is available
def check_local_repo(repo_dir, repo_url):

  if not os.path.exists(repo_dir):
    print ('- Fail: could not compare! The expected local repository directory %s is not found!' % repo_dir)
    print ('Update your project by invoking a command given below:\n')
    print ('git pull --recurse-submodules\n')
    sys.exit(1)

# report difference between configuration files in the given directories
def report_diff_files(working_dir, repo_dir):

  dircmp = filecmp.dircmp(working_dir, repo_dir)
  n_diff_files = 0

  # list with different files in both working and local repo directories
  if len(dircmp.diff_files) != 0:
    n_diff_files += len(dircmp.diff_files)
    print ('### Generated files: %s ###' % len(dircmp.diff_files))

    for diff_file in dircmp.diff_files:
      print (diff_file)

  # list with different files only in the output working directory
  if len(dircmp.left_only) != 0:
    n_diff_files += len(dircmp.left_only)
    print ('### New files that are not in repo: %s  ###' % len(dircmp.left_only))

    for left_only_file in dircmp.left_only:
      print (left_only_file)

  # list with different files only in the local repo (eg, special configuration created manually)
  if len(dircmp.right_only) != 0:
    n_diff_files += len(dircmp.right_only)
    print ('### Special files that are only in repo: %s ###' % len(dircmp.right_only))
    print ('### You might also need to update these special files manually! ###')

    for right_only_file in dircmp.right_only:
      print (right_only_file)

  if n_diff_files == 0:
    print ('+ PASS: No difference between configuration files in %s and %s' % (working_dir, repo_dir))

  return n_diff_files

# get a list with different configuration files
def get_diff_files(working_dir, repo_dir):

  dircmp = filecmp.dircmp(working_dir, repo_dir)

  #TODO: how about existing files only in local repo (eg, special configuration created manually)
  # dircmp.right_only

  # list with different files in both working and local repo directories
  # list with different files only in the output working directory
  return dircmp.diff_files + dircmp.left_only

# update the local repo to its latest commits
def update_local_repo(repo_dir):

  # In this project the local configuration repo for the TN2 configuration is used as a submodule.
  # It means that its upstream repo can have the latest changes that are not yet specified by the main repo of this project.
  # Therefore, the 'git submodule update' command cannot pull such latest commits:
  # - this command sets the submodules to the commit specified by the main/parent repository.
  # Hence, the local repo is updated directly with the 'git pull' command.

  print ('? Info: updating the local repo with the latest changes from its upstream repo')
  args = 'cd ' + repo_dir + ' && ' + 'git pull' # change to the local repo
  try:
    subprocess.check_call(args, shell=True)
  except subprocess.CalledProcessError as e:
    print ('Error: %s' % e)
    sys.exit(e.returncode)

# copy newly generated configurations to the local configuration repo
def copy_config(dot_configs, src_dir, dst_dir):

  for dc_file in dot_configs:
    try:
      src_file = os.path.join(src_dir, dc_file)
      shutil.copy2(src_file, dst_dir)
      print ('+ %s' % dc_file)
    except (IOError, os.error) as why:
      print((dc_file, dst_dir, str(why)))

# exit if user refuses a prompted action
def exit_on_user_reaction(answer, exit_char):

  if answer != '' and str(answer).lower()[0] == exit_char:
    print ('User disagreed. Exit!')
    sys.exit(0)

# remind an user to commit the main/parent repo with changes in the specified submodule
def remind_user(repo_dir):

  print ('\n### IMPORTANT: Do not forget to commit and push changes in the local repo (%s)!' % repo_dir)
  print ('You can invoke \'git status\' to see the changes\n')

# do all
if __name__ == '__main__':

  # check if the local repo with TN2 configuration is available
  check_local_repo(common.TN2_CONFIG_REPO_DIR, common.TN2_CONFIG_REPO_URL)

  # update the local configuration repo with the latest changes from its upstream repo
  update_local_repo(common.TN2_CONFIG_REPO_PATH)

  # check if the output working directory is available
  check_output_dir(common.WRS_DOT_CONFIG_DIR)

  # report difference between generated and existing configuration files
  if report_diff_files(common.WRS_DOT_CONFIG_DIR, common.TN2_CONFIG_REPO_DIR):

    # get a list with different configuration files
    dot_configs = get_diff_files(common.WRS_DOT_CONFIG_DIR, common.TN2_CONFIG_REPO_DIR)

    if len(dot_configs) != 0:
      # ask user about to update the local repo
      answer = raw_input('\n### Would you like to update the LOCAL configuration repository with the generated configurations? (Y/n): ')
      exit_on_user_reaction(answer, 'n')

      # copy newly generated configurations to the local configuration repo
      copy_config(dot_configs, common.WRS_DOT_CONFIG_DIR, common.TN2_CONFIG_REPO_DIR)

    else:
      print ('+ Pass: At least no new configuration file is detected!')

    # report difference between generated and existing configuration files
    report_diff_files(common.WRS_DOT_CONFIG_DIR, common.TN2_CONFIG_REPO_DIR)

    # remind an user to commit the main/parent repo with changes in the specified submodule
    remind_user(common.TN2_CONFIG_REPO_PATH)
