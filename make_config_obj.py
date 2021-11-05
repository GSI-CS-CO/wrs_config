#!/usr/bin/env python

import copy, json, os
from getpass import getuser as gp_getuser
from socket import gethostname as sk_gethostname
import subprocess

# VLAN definitions, WRS port roles, WRS layers
vlans_file = 'vlans.json'
port_roles_file = 'port_roles.json'
switch_layer_file = 'switch_layers.json'

# WRS configuration object (JSON) compatible with the CERN config generator
config_obj_file = 'dot-config.json'

# files required to set VLAN configurations
item_files = [vlans_file, port_roles_file,
                 switch_layer_file, config_obj_file]

# user input file with a list of WRSs
switches_file = 'switches.json'

# output WRS configuration with VLAN settings (prefixed with WRS name)
output_file = 'dot-config_'

def get_git_hash():
  # Return short commit hash in Git

  git_hash = None
  args = 'git rev-parse --short HEAD'
  try:
    git_hash = subprocess.check_output(args, shell=True)
    git_hash = git_hash.decode("utf-8").strip('\n')
  except subprocess.CalledProcessError as e:
    print ('Error: Failed to get short Git hash!')
    print (e)

  return git_hash

def check_git_status():
  # Return empty value if Git working tree is clean

  git_status = None
  args = 'git status --porcelain --untracked-files=no'
  try:
    git_status = subprocess.check_output(args, shell=True)
    git_status = git_status.decode("utf-8").strip('\n')
  except subprocess.CalledProcessError as e:
    print ('Error: Failed to check Git status!')
    print (e)

  return git_status

def get_items(json_files):

  # Get the VLAN definitions, port roles, WRS layers, default WRS configuration
  # from the given JSON files.

  items = {}

  for file_path in json_files:
    with open(file_path, 'r') as jf:
      parsed_items = json.load(jf)
      ##print(json.dumps(parsed_items, indent=2, sort_keys=True))

      if parsed_items is not None:
        file_name = os.path.basename(file_path)
        item_name = file_name.split('.')[0]
        items[item_name] = parsed_items

  return items

def evaluate_rvid(items, vlans, extern_vid):

  # Return a list of VIDs for routing (RVIDs).
  rvids = []

  if isinstance(vlans, list):
    for vlan in vlans:
      if isinstance(vlan, dict):
        if 'ref' in vlan:
          if vlan['ref'] in items:
            ref = vlan['ref']
            name = vlan['name']
            rvids.append(copy.deepcopy(items[ref][name]['vid']))
          elif '#extern' in vlan['ref']:
            rvids.append(extern_vid)
      else:
        rvids.append(vlan)

  return rvids

def evaluate_vid(items, vlan, extern_vid):

  # Return VLAN ID (VID) if 'vlan' has valid value, otherwise None.
  if vlan is None:
    return vlan

  vid = None
  if isinstance(vlan, dict):
    if 'ref' in vlan:
      if vlan['ref'] in items:
        ref = vlan['ref']
        name = vlan['name']
        vid = items[ref][name]['vid']
      elif '#extern' in vlan['ref']:
        vid = extern_vid
  else:
    vid = vlan

  return vid

def configure_ports(items, vlan, wrs_port_model):

  # Set the VLAN parameters to all ports of 'wrs_port_model' based on
  # the pre-defined WRS layer (in 'items') and 'vlan'

  # get VLAN ID (VID) to which the given switch belongs
  vid = evaluate_vid(items, vlan, None)

  if vid is None:
    print ('Error: Null VID')
    return

  ports = wrs_port_model['ports']
  for idx in ports.keys():
    if isinstance(ports[idx]['role'], dict):
      role_keys = ports[idx]['role'].keys()
      if 'ref' in role_keys and 'name' in role_keys:
        ref = ports[idx]['role']['ref']
        name = ports[idx]['role']['name']
        role = copy.deepcopy(items[ref][name])

        role['pvid'] = evaluate_vid(items, role['pvid'], vid)
        role['ptp_vid'] = evaluate_vid(items, role['ptp_vid'], vid)
        role['rvid'] = evaluate_rvid(items, role['rvid'], vid)

        wrs_port_model['ports'][idx]['role'] = role
        ##print (idx, name, port[idx]['role'])

def build_rtu_config(items, wrs_port_model):

  # Build RTU configuration part included in VLANs configuration
  rtu_config = {}

  # extract per-VLANs configuration from 'wrs_port_model'
  ports_map = wrs_port_model['ports']
  for port in ports_map:
    roleConfig = ports_map[port]['role']

    if 'rvid' in roleConfig:
      for v in roleConfig['rvid']:
        port_num = int(port)
        if v in rtu_config:
          rtu_config[v]['ports'].append(port_num)
        else:
          rtu_config[v] = {'ports':[port_num]}

    elif roleConfig != 'default':
      print('Extract VLANs failed: bad role for port ' + port)

  # format RTU configuration ready for WRS configuration object
  if len(rtu_config):
    # sort ports and convert them to single str
    for v in rtu_config:
      ports = sorted(rtu_config[v]['ports'])
      ports = [str(i) for i in ports]

      ports_str = ';'.join(ports)
      rtu_config[v]['ports'] = ports_str

    # add 'fid'
    vlan_items = copy.deepcopy(items['vlans'])
    for v in vlan_items:
      if 'vid' in vlan_items[v]:
        vid = vlan_items[v]['vid']

        if vid in rtu_config:
          rtu_config[vid]['fid'] = vlan_items[v]['fid']

          # 'ports' option is exception: if it's given, then frames must be forwarded only to the given ports
          if 'ports' in vlan_items[v]:
            exceptional_ports = vlan_items[v]['ports']

            if exceptional_ports =='19':   # eCPU is linked to port 19, so remove all other ports (VLAN entry with fid is sufficient)
               rtu_config[vid].pop('ports', None)

  #print (json.dumps(rtu_config))
  return rtu_config

def build_config_obj(items, wrs_port_model, rtu_config, switch):

  # Build WRS configuration object (in JSON) compatible with the CERN tool.
  # items: VLAN definitions, port roles, WRS layers, default config object
  # wrs_port_model: WRS port-model with VLANs configuration
  # rtu_config: per-VLAN RTU configuration
  # switch: object with switch name and role

  config_obj = copy.deepcopy(items['dot-config']) # deep-copy of mutables
  build_info = gp_getuser() + '@' + sk_gethostname()
  if items['git_hash'] is not None:
    build_info += ';' + 'git_hash=' + items['git_hash']
  if switch['name'] is not None:
    build_info += ';' + 'role=' + switch['name']
  config_obj['requestedByUser'] = build_info

  # configurationItems
  # - WRS timing mode: Grand Master, Boundary Clock, Free-running Master
  # - Enable VLANs
  item_config_time = 'CONFIG_TIME_' + wrs_port_model['timing_mode']
  item_config_vlan_enable = 'CONFIG_VLAN_ENABLE'

  config_items = []                     # tmp list
  for item in config_obj['configurationItems']:
    if item['itemConfig'] == item_config_time:  # update WRS timing
      item['itemValue'] = 'true'
    elif item['itemConfig'] == item_config_vlan_enable: # enable VLANs
      item['itemValue'] = 'true'
    config_items.append(item)           # update tmp list
  config_obj['configurationItems'] = config_items # update old list with tmp list

  # configPorts
  config_items = []
  for port in config_obj['configPorts']:
    if port['portNumber'] in wrs_port_model['ports']:

      roleConfig = wrs_port_model['ports'][port['portNumber']]['role']
      if 'ptp_mode' in roleConfig and roleConfig['ptp_mode'] != 'none':
        port['ptpRole'] = roleConfig['ptp_mode']

      config_items.append(port)

  config_obj['configPorts'] = config_items

  # configRvlan
  if 'rvlan' in switch: # non-default settings for RVLAN
    for key in switch['rvlan']:
      config_obj['configRvlan'][key] = switch['rvlan'][key]

  # configVlanPorts
  config_items = []
  for port in config_obj['configVlanPorts']:
    if port['portNumber'] in wrs_port_model['ports']:

      roleConfig = wrs_port_model['ports'][port['portNumber']]['role']
      if 'port_mode' in roleConfig:
        if roleConfig['port_mode'] != 'unqualified':
          port['vlanPortMode'] = roleConfig['port_mode']
          port['vlanPortUntag'] = 'false'
          if roleConfig['port_mode'] == 'access':
            port['vlanPortUntag'] = 'true'
          elif roleConfig['port_mode'] == 'trunk':
            port['vlanPortLldpTxVid'] = items['vlans']['lldp_tx']['vid']

      if 'ptp_vid' in roleConfig:
        port['vlanPortPtpVidEnabled'] = 'y'
        if roleConfig['ptp_vid'] is not None:
          port['vlanPortPtpVid'] = roleConfig['ptp_vid']

      if 'pvid' in roleConfig:
        if roleConfig['pvid'] is not None:
          port['vlanPortVid'] = roleConfig['pvid']

      config_items.append(port)

  config_obj['configVlanPorts'] = config_items

  # configVlans
  if len(rtu_config):
    config_obj['configVlans'] = []
    for v in rtu_config:
      config = {'prio': None, 'drop': 'false', 'ports': None}
      config['vid'] = v
      config['fid'] = rtu_config[v]['fid']
      if 'ports' in rtu_config[v]:           # 'ports' is empty if forwarding is allowed only to port 19 (eCPU)
        config['ports'] = rtu_config[v]['ports']
      config_obj['configVlans'].append(config)

  return config_obj

def update_optional(items, wrs_config_obj, optionals):
  # Update non-VLAN, non-port specific options of configuration object

  for key in optionals:
    # look for WRS root password and its encryption
    if 'cipher' in key and optionals[key] == 'enabled':
      # get corresponding itemConfig
      for ci in wrs_config_obj['configurationItems']: # assume wrs_config_obj['configurationItems'] is avaialable
        # set cipher and enable configuration
        if 'CONFIG_ROOT_PWD_IS_ENCRYPTED' in ci['itemConfig']:
          ci['itemValue'] = "true"
        if 'CONFIG_ROOT_PWD_CYPHER' in ci['itemConfig']:
          ci['itemValue'] = items['cipher']
    elif optionals[key] is not None:                  # general CONFIG_* option that has custom value (eg, CONFIG_NTP_SERVER)
      # get corresponding itemConfig
      for ci in wrs_config_obj['configurationItems']:
        # set a custom value
        if key in ci['itemConfig']:
          ci['itemValue'] = optionals[key]

def generate_root_passwd_cipher():
  # Generate MD5 cipher for WRS root password input by user

  cipher = None

  # prompt user to input root password
  try:
    plain_password = raw_input('### Enter WRS root password ###: ') # worked with 2.7
  except NameError:
    plain_password = input('### Enter WRS root password ###: ') # works with 3.8

  # crypt has no attribute METHOD_MD5 in Python 2.7
  #cipher = crypt.crypt(plain, crypt.METHOD_MD5)

  args = 'mkpasswd -5 ' + plain_password
  try:
    cipher = subprocess.check_output(args, shell=True)
    cipher = cipher.decode("utf-8").strip('\n')
  except subprocess.CalledProcessError as e:
    print ('Error: Failed to create WRS root password cipher!')
    print (e)

  return cipher

def make(switches, out_dir):

  # Build WRS configuration object (JSON) for a given switch instance in 'switches'
  global item_files

  # get required items (VLAN definitions, port roles, WRS layers, config object)
  items = get_items(item_files)
  ##print(json.dumps(items,indent=2))

  # break if all required items are not avialable
  if len(items) != len(item_files):
    print ('failure in required files!')
    return -1

  # look for optional configuration options (eg, encrypted WRS root password)
  for switch in switches['devices']:
    if 'optional' in switch and switch['optional'] is not None:
      optionals = switch['optional']

      # generate WRS root password cipher if it's enabled
      for key in optionals:
        if 'cipher' in key and optionals[key] == 'enabled':
          cipher = generate_root_passwd_cipher()
          if cipher is not None:
            items['cipher'] = cipher
            print (items['cipher'])
            break

      # break if cipher is set
      if 'cipher' in items and items['cipher'] is not None:
        break

  # get commit hash of HEAD
  items['git_hash'] = get_git_hash()
  if len(check_git_status()):
    items['git_hash'] += '-dirty'

  # build configuration objects for given switches
  for switch in switches['devices']:
    # get a configurable WRS port-model
    wrs_port_model = copy.deepcopy(items['switch_layers'][switch['layer']])

    # set VLANs configuration to the WRS port-model
    configure_ports(items, switch['vlan'], wrs_port_model)

    # extract RTU configuration (per-VLAN config) from the WRS port-model
    rtu_config = build_rtu_config(items, wrs_port_model)

    # build WRS config object from WRS port-model (with VLANs configuration) and
    # RTU configuration
    wrs_config_obj = build_config_obj(items, wrs_port_model, rtu_config, switch)

    # update optional configuration (non-VLAN, non-port specific)
    if 'optional' in switch and switch['optional'] is not None:
      update_optional(items, wrs_config_obj, switch['optional'])

    # write WRS configuration object to file
    file_name = output_file + switch['name'] + '.json'
    file_path = os.path.join(out_dir, file_name)
    with open(file_path, 'w') as out_file:
      out_file.write(json.dumps(wrs_config_obj, indent=2, sort_keys=True))

    ##file_name = output_file + switch['name'] + '_vlan.json'
    ##file_path = os.path.join(out_dir, file_name)
    ##with open(file_path, 'w') as out_file:
      ##out_file.write(json.dumps(wrs_port_model, indent=2, sort_keys=True))

  return 0

if __name__ == '__main__':

  import argparse, sys

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

  # make WRS configuration objects
  sys.exit(make(switches))

