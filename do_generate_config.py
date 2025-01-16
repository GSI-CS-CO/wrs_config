#!/usr/bin/env python3

# Script tool to generate WRS configuration (dot-config)
# The configuration is generated in 2 steps:
# - make confgiuration object (dot-config_<WRS_layer>.json)
# - generate configuration (dot-config_<WRS_layer>)
# where <WRS_layer> can be any of:
# - grand_master, service, prod_local_master, prod_distrib, prod_access

import argparse, sys, os, json
import make_config_obj
import make_port_model
import set_calibration_values   # WRS v7.0: generate dot-configs for all HW versions (3.3 & 3.4)

# output folder to store configuration files
config_prefix = 'dot-config_'
config_dir = 'output/config'
object_dir = 'output/object'
graph_dir = 'output/graph'
config_generator_dir = 'wrs-config-generator'
config_generator_url = 'https://gitlab.cern.ch/white-rabbit/wrs-config-generator'

# calibration values are stored in external files
wrs_calib_filepath_prefix='calibration_values_'

def generate_config_object(switches, object_dir):
  make_config_obj.make(switches, object_dir)

def generate_config(switches, object_dir, config_dir):

  for switch in switches['devices']:

    for hw_ver in make_config_obj.supported_hw_versions:

      # file paths of configuration object and dot-config file
      object_filepath = os.path.join(object_dir, config_prefix + switch['name'] + '_' + hw_ver)
      config_filepath = os.path.join(config_dir, config_prefix + switch['name'] + '_v' + hw_ver)

      # generate configuration (shell command)
      os.system('python3 wrs-config-generator/generate_config.py --json=' + object_filepath + '.json --config=' + config_filepath)

def generate_port_model(switches, config_dir, graph_dir=None):

  for switch in switches['devices']:

    for hw_ver in make_config_obj.supported_hw_versions:

      # configuration file path
      config_filepath = os.path.join(config_dir, config_prefix + switch['name'] + '_v' + hw_ver)

      # graph file path
      if graph_dir == None:
        graph_dir=config_dir

      graph_filepath = os.path.join(graph_dir, config_prefix + switch['name'] + '_v' + hw_ver)

      make_port_model.make(config_filepath, graph_filepath)

def update_calibration_values(wrs_sw_ver="7.0"):

  for switch in switches['devices']:
    for hw_ver in make_config_obj.supported_hw_versions:

      # file path of configuration dot-config file
      config_filepath = os.path.join(config_dir, config_prefix + switch['name'] + '_v' + hw_ver)

      # path to file with calibration values
      wrs_calib_filepath = wrs_calib_filepath_prefix + wrs_sw_ver

      # set the calibration values (no need to check)
      set_calibration_values.set(config_filepath, wrs_calib_filepath, wrs_sw_ver, hw_ver)

def create_folder(directory):
  try:
    if not os.path.exists(directory):
      os.makedirs(directory)
  except OSError:
    print ('Error: Could not create directory ' +  directory)
    sys.exit(1)

def get_fw_version(filepath):

  # Parse and get the actual FW version from dot-config (json)
  with open(filepath, 'r') as f:
    json_configs = json.load(f)

  # Check if an object for FW version is found
  if set_calibration_values.config_sw_ver in json_configs:
    return json_configs[set_calibration_values.config_sw_ver]

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
  create_folder(graph_dir)

  # generate WRS configuration objects
  generate_config_object(switches, object_dir)

  # generate WRS configurations
  generate_config(switches, object_dir, config_dir)

  # get the FW version from 'dot-config.json' (needed to set the calibration values)
  wrs_fw_ver = get_fw_version(make_config_obj.config_obj_file)

  # set the calibration values
  update_calibration_values(wrs_fw_ver)

  # generate WRS port model
  generate_port_model(switches, config_dir, graph_dir)
