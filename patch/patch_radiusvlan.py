'''
New release of the WRS firmware is going to support the RADIUS authentication.
This patch will apply new configuration options required for the radiusvlan tool.
'''

import re, os

vlan_enable_regex = None
rvlan_disabled_dot_configs = ['dot-config_production_service'] # configuration files in which radiusvlan is disabled by default

config_options_rvlan_title=[
  '#',
  '# RADIUS VLAN options',
  '#']

config_options_rvlan_enable = 'CONFIG_RVLAN_DAEMON='

config_options_rvlan_body=[
  'CONFIG_RVLAN_PMASK="ffffffff"',
  'CONFIG_RVLAN_AUTH_VLAN=4093',
  'CONFIG_RVLAN_NOAUTH_VLAN=4094',
  'CONFIG_RVLAN_RADIUS_SERVERS="192.168.16.181,192.168.16.182"',
  'CONFIG_RVLAN_RADIUS_SECRET="auhei8Ha"',
  'CONFIG_RVLAN_OBEY_DOTCONFIG=y']

def apply_pretty(file_path):

  global vlan_enable_regex

  if vlan_enable_regex is None:
    vlan_enable_regex = re.compile(r'(^CONFIG_VLANS_ENABLE=(?P<value>.*$))') # CONFIG_VLANS_ENABLE=y

  lines = []
  vlan_enable_head = None
  vlan_enable_value = 'n'
  disable_rvlan = False

  if os.path.basename(file_path) in rvlan_disabled_dot_configs:    # rvlan is disabled by default in some dot-configs (eg, production_service)
    disable_rvlan = True

  with open(file_path, 'r') as f:
    lines = f.readlines()

  new_line = '\n'

  for index in range(len(lines)):

    vlan_enable_match = vlan_enable_regex.match(lines[index])
    if vlan_enable_match is not None:
      vlan_enable_head = index                                     # VLANs are enabled (option head)
      if not disable_rvlan:                                        # parse a value of 'VLAN enable' only if radiusvlan is allowed
        vlan_enable_value = vlan_enable_match.group('value')

    if vlan_enable_head is not None and lines[index] == new_line:  # VLANs are enabled (option tail)

      for option in config_options_rvlan_title:                    # insert a title of the radius_vlan options
        index += 1
        lines.insert(index, option + new_line)

      lines.insert(index + 1, new_line)                            # insert radius_vlan enable option
      lines.insert(index + 2, config_options_rvlan_enable + vlan_enable_value)
      lines.insert(index + 3, new_line)

      index += 3
      for option in config_options_rvlan_body:                     # insert radius_vlan options
        index += 1
        lines.insert(index, option + new_line)

      lines.insert(index + 1, new_line)

      with open(file_path, 'w') as f:
        f.writelines(lines)

      break

if __name__ == '__main__':

  import argparse, os, sys

  parser = argparse.ArgumentParser(prog=sys.argv[0],
    description='Append RVLAN options to the WRS configuration file')
  parser.add_argument('config_file', help='path to configuration file')

  # command options
  opts = parser.parse_args(sys.argv[1:])

  # path to the WRS configuration file
  config_path = os.path.abspath(opts.config_file)

  # update file
  apply(config_path)
