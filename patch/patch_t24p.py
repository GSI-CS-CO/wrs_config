'''
Apply the missing T24P_TRANS_POINT option in dot-config directly.

If the option is not given, then WRS reports the PTP timing error:
WR-SWITCH-MIB::wrsTimingStatus.0 = INTEGER: error(2)
WR-SWITCH-MIB::wrsPTPStatus.0 = INTEGER: error(2)
'''

import re
import fileinput

wr_profile_regex = None
t24p_file = 't24p.json'

def apply(lines, t24p_values):

  #CONFIG_PORT<18>_INST<01>_INGRESS_LATENCY=
  global wr_profile_regex

  new_lines = []

  if wr_profile_regex is None:
    wr_profile_regex = re.compile(r'(?P<option>CONFIG_PORT(?P<port>[0-9]+)_INST(?P<inst>[0-9]+)_INGRESS_LATENCY=.*)')

  for line in lines:

    new_lines.append(line)
    match = wr_profile_regex.match(line)

    if match is not None:
      port = match.group('port')
      instance = match.group('inst')
      value = t24p_values[port]
      new_line = 'CONFIG_PORT%s_INST%s_T24P_TRANS_POINT=%s\n' % (port, instance, value)
      new_lines.append(new_line)

  return new_lines


def apply_inplace(file_path, t24p_values):

  global wr_profile_regex

  if wr_profile_regex is None:
    wr_profile_regex = re.compile(r'(?P<option>CONFIG_PORT(?P<port>[0-9]+)_INST(?P<inst>[0-9]+)_INGRESS_LATENCY=.*)')

  for line in fileinput.FileInput(file_path, inplace=1):
    match = wr_profile_regex.match(line)

    if match is not None:
      port = match.group('port')
      instance = match.group('inst')
      value = t24p_values[port]
      new_line = 'CONFIG_PORT%s_INST%s_T24P_TRANS_POINT=%s\n' % (port, instance, value)
      line = line.replace(line, line+new_line)

    print line,

if __name__ == '__main__':

  import argparse, os, sys, json

  parser = argparse.ArgumentParser(prog=sys.argv[0],
    description='Add T24P option to configuration file')
  parser.add_argument('config_file', help='path to configuration file')
  parser.add_argument('patch_file', help='path to patch file')

  # command options
  opts = parser.parse_args(sys.argv[1:])

  # path to the configuration and patch files
  config_path = os.path.abspath(opts.config_file)
  patch_path = os.path.abspath(opts.patch_file)

  # update file
  t24p_values = {}
  with open(patch_path, 'r') as f:
    t24p_values = json.load(f)

  if t24p_values is not None:
    apply_inplace(config_path, t24p_values)

'''if __name__ == '__main__':

  import argparse, os, re, sys

  parser = argparse.ArgumentParser(prog=sys.argv[0],
    description='Patch T24P option to configuration')
  parser.add_argument('file', help='path to configuration file')

  # command options
  opts = parser.parse_args(sys.argv[1:])

  # path to the configuration file
  path = os.path.abspath(opts.file)

  lines = []
  modified_lines = []
  with open(path, 'r') as f:
    lines = f.readlines()
    modified_lines = apply(lines, t24p_values)

  if modified_lines is not None:
    modified_lines = "".join(modified_lines)
    with open(path, 'w') as f:
      f.write(modified_lines)
'''
