'''
New release of the WRS firmware is going to support the RADIUS authentication.
This patch will apply new configuration options required for the radiusvlan tool.
'''

import re

vlan_enable_regex = None

config_options_rvlan=[
  '#',
  '# RADIUS VLAN options',
  '#',
  '',
  'CONFIG_RVLAN_DAEMON=y',
  'CONFIG_RVLAN_PMASK="ffffffff"',
  'CONFIG_RVLAN_AUTH_VLAN=4093',
  'CONFIG_RVLAN_NOAUTH_VLAN=4094',
  'CONFIG_RVLAN_RADIUS_SERVERS="192.168.16.181,192.168.16.182"',
  'CONFIG_RVLAN_RADIUS_SECRET="auhei8Ha"',
  'CONFIG_RVLAN_OBEY_DOTCONFIG=y']

def apply(file_path):

  global vlan_enable_regex

  if vlan_enable_regex is None:
    vlan_enable_regex = re.compile(r'(^CONFIG_VLANS_ENABLE=y)') # CONFIG_VLANS_ENABLE=y

  with open(file_path, 'a+') as f:                              # open a file with read and append accesses
    for line in f:
      vlan_enable_match = vlan_enable_regex.match(line)
      if vlan_enable_match is not None:                         # VLANs are enabled
        for option in config_options_rvlan:                     # append all radius_vlan options
          f.write("%s\n" % option)
        break

def apply_pretty(file_path):

  global vlan_enable_regex

  if vlan_enable_regex is None:
    vlan_enable_regex = re.compile(r'(^CONFIG_VLANS_ENABLE=y)') # CONFIG_VLANS_ENABLE=y

  lines = []
  vlan_enable_match = None

  with open(file_path, 'r') as f:
    lines = f.readlines()

  new_line = '\n'

  for index in range(len(lines)):

    if vlan_enable_regex.match(lines[index]) is not None:
      vlan_enable_match = index                                     # VLANs are enabled (option head)

    if vlan_enable_match is not None and lines[index] == new_line:  # VLANs are enabled (option tail)

      for option in config_options_rvlan:                           # insert all radius_vlan options
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
