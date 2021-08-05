#!/usr/bin/env python

# This script is used to commit the generated WRS configurations to
# to the remote repository.

import os, sys, glob, subprocess, shutil, filecmp
import config_common as cc

# get a list with the generated configurations
def get_dot_config(dot_config_path):

  dc_list = glob.glob(dot_config_path)
  if dc_list is None:
    print ('Error: %s not found' % cc.CONFIG_PREFIX)
    sys.exit(1)
  else:
    return dc_list

# get a list with different configuration files
def get_diff_files(working_dir, local_repo_dir):

  dircmp = filecmp.dircmp(working_dir, local_repo_dir)

  # list with different files in both working and local repo directories
  #for diff_file in dircmp.diff_files:
    #print (diff_file)

  # list with different files only in working directory
  #for left_only_file in dircmp.left_only:
    #print (left_only_file)

  #TODO: how about existing files only in local repo
  # dircmp.right_only

  return dircmp.diff_files + dircmp.left_only

# ask the git commit message and git tag
def get_commit_message():

  commit_msg = ''
  while commit_msg == '':
    commit_msg = raw_input('### Please provide your commit msg ###: ')

  return commit_msg

# clone/pull the configuration repo
def clone_config_repo(url):

  args = 'git clone ' + url
  print (args)
  try:
    subprocess.call(args, shell=True)
  except subprocess.CalledProcessError as e:
    print ('Error: Could not clone git repo %s' % url)
    print (e)

# update the local configuration repo with newly generated configurations
def update_local_repo(dot_configs, src_dir, dst_dir):

  errors = []
  for dc_file in dot_configs:
    try:
      src_file = os.path.join(src_dir, dc_file)
      shutil.copy2(src_file, dst_dir)
      print ('+ %s' % dc_file)
    except (IOError, os.error) as why:
      errors.append((dc_file, dst_dir, str(why)))

  if errors:
    raise Error(errors)
  else:
    print ('+ updated the local config repo')

# commit and push the new configurations
def commit_local_repo(commit_msg):

  args = 'git commit -m "%s"' % commit_msg
  print (args)
  try:
    subprocess.call(args, shell=True)
  except subprocess.CalledProcessError as e:
    print ('Error: Could not commit the local changes')
    print (e)

def push_to_remote_repo():

  args = 'git push -u origin master'
  print (args)
  try:
    subprocess.call(args, shell=True)
  except subprocess.CalledProcessError as e:
    print ('Error: Could not push the commits')
    print (e)

# exit if user refuses a prompted action
def exit_on_user_reaction(answer):

  if answer == '' or str(answer).lower()[0] == 'n':
    print ('User disagreed. Exit!')
    sys.exit(0)

# do all
if __name__ == '__main__':

  # list the generated dot-config_* files
  #dot_configs = get_dot_config(os.path.join(cc.WRS_DOT_CONFIG_DIR, cc.CONFIG_PREFIX + '*'))
  #print (dot_configs)

  # get a list with different configuration files
  dot_configs = get_diff_files(cc.WRS_DOT_CONFIG_DIR, cc.TN2_CONFIG_REPO_DIR)
  #print (dot_configs)

  # ask user about to update the local repo
  answer = raw_input('### Would you like to update the LOCAL configuration repository? (y/N): ')
  exit_on_user_reaction(answer)

  commit_msg = get_commit_message()
  print ('Your commit will be: %s' % commit_msg)

  # make sure that user really would like to update the local repo
  answer = raw_input('### Are you really sure to update the LOCAL configuration repository? (y/N): ')
  exit_on_user_reaction(answer)

  update_local_repo(dot_configs, cc.WRS_DOT_CONFIG_DIR, cc.TN2_CONFIG_REPO_DIR)
  commit_local_repo(commit_msg)

  # ask user about to update the local repo
  answer = raw_input('### Hey, you achieved the last step!\n### Do you also want to update the REMOTE configuration repository? (Y/n): ')
  exit_on_user_reaction(answer)

  push_to_remote_repo()

