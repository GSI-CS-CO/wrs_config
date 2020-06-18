#!/usr/bin/env python

# Script tool to generate WRS configuration (dot-config)
# The configuration is generated in 2 steps:
# - make confgiuration object (dot-config_<WRS_layer>.json)
# - generate configuration (dot-config_<WRS_layer>)
# where <WRS_layer> can be any of:
# - grand_master, service, prod_local_master, prod_distrib, prod_access

import argparse, sys, os, json
import make_config_obj
import make_port_model
import patch.patch_t24p as patch_t24p

# output folder to store configuration files
config_prefix = 'dot-config_'
config_dir = 'output/config'
object_dir = 'output/object'
config_generator_dir = 'wrs-config-generator'
config_generator_url = 'https://gitlab.cern.ch/white-rabbit/wrs-config-generator'
patch_t24p_path = 'patch/t24p.json'

def generate_config_object(switches, object_dir):
  make_config_obj.make(switches, object_dir)

def generate_config(switches, object_dir, config_dir):

  for switch in switches['devices']:

    # file paths of configuration object and dot-config file
    object_filepath = os.path.join(object_dir, config_prefix + switch['name'])
    config_filepath = os.path.join(config_dir, config_prefix + switch['name'])

    # generate configuration (shell command)
    os.system('python wrs-config-generator/generate_config.py --json=' + object_filepath + '.json --config=' + config_filepath)

def generate_port_model(switches, config_dir):

  for switch in switches['devices']:

    # configuration file path
    config_filepath = os.path.join(config_dir, config_prefix + switch['name'])

    make_port_model.make(config_filepath)

def create_folder(directory):
  try:
    if not os.path.exists(directory):
      os.makedirs(directory)
  except OSError:
    print ('Error: Could not create directory ' +  directory)
    sys.exit(1)

def apply_patch(switches, config_dir):

  # update file
  t24p_values = {}
  with open(patch_t24p_path, 'r') as f:
    t24p_values = json.load(f)

  if t24p_values is not None:

    # for each switch apply T24P patch
    for switch in switches['devices']:

      config_filepath = os.path.join(config_dir, config_prefix + switch['name'])

      patch_t24p.apply_inplace(config_filepath, t24p_values)

if __name__ == '__main__':

  # Check if CERN tool is available
  if not os.path.exists(config_generator_dir):
    print ('Error: CERN tool is missing, please download it from ' + config_generator_url)
    sys.exit(1)

  # Set up command-line arguments
  parser = argparse.ArgumentParser(prog = sys.argv[0],
            description = 'Build WRS configurations with VLAN settings in JSON')
  parser.add_argument('file', help = 'Path to a file with a list of WRSs')

  # Get command-line arguments
  args = parser.parse_args(sys.argv[1:])

  switches_file = os.path.abspath(args.file)

  # Read user input file
  switches = {}
  with open(switches_file, 'r') as in_file:
    switches = json.load(in_file)  # parse JSON file to python obj (dict)

  # create output folders if they don't exist
  create_folder(config_dir)
  create_folder(object_dir)

  # generate WRS configuration objects
  generate_config_object(switches, object_dir)

  # generate WRS configurations
  generate_config(switches, object_dir, config_dir)

  # apply T24P patch
  apply_patch(switches, config_dir)

  # generate WRS port model
  generate_port_model(switches, config_dir)