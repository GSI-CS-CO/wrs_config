'''
New release of the WRS firmware is going to fix an issue with
the LLDP discovery when VLANs are used.

Apply new configuration options to each wri port to allow the LLDP discovery:
- CONFIG_VLANS_PORTxx_LLDP_TX_VID should have a dedicated value (trunk port
  mode), otherwise empty (access, disabled, unqualified port modes)
- CONFIG_VLANS_PORTxx_LLDP_TX_PRIO should be zero by default
'''

import re
import fileinput

ptp_vid_regex = None
mode_trunk_regex = None
trunk_port = None
vid_file = 'vid.json'

def apply_inplace(file_path, lldp_vid = ""):

  global ptp_vid_regex, mode_trunk_regex, trunk_port

  if mode_trunk_regex is None:
    mode_trunk_regex = re.compile(r'(?P<option>CONFIG_VLANS_PORT(?P<port>[0-9]+)_MODE_TRUNK=y)') # CONFIG_VLANS_PORTxx_MODE_TRUNK=y

  if ptp_vid_regex is None:
    ptp_vid_regex = re.compile(r'(?P<option>CONFIG_VLANS_PORT(?P<port>[0-9]+)_PTP_VID=(?P<value>.*$))') # CONFIG_VLANS_PORTxx_PTP_VID="vid"

  for line in fileinput.FileInput(file_path, inplace=1):
    mode_trunk_match = mode_trunk_regex.match(line)
    ptp_vid_match = ptp_vid_regex.match(line)

    if mode_trunk_match is not None:
      trunk_port = mode_trunk_match.group('port')

    if ptp_vid_match is not None:
      ptp_port = ptp_vid_match.group('port')

      if ptp_port == trunk_port:  # trunk port mode
        new_lines = 'CONFIG_VLANS_PORT%s_LLDP_TX_VID="%s"\n' % (ptp_port, lldp_vid) # LLDP_TX_VID="lldp_vid"
      else:
        new_lines = 'CONFIG_VLANS_PORT%s_LLDP_TX_VID=""\n' % (ptp_port)          # LLDP_TX_VID=""

      new_lines += 'CONFIG_VLANS_PORT%s_LLDP_TX_PRIO=0\n' % (ptp_port)           # LLDP_TX_PRIO=0
      line = line.replace(line, line+new_lines)
      trunk_port = None

    print line,

if __name__ == '__main__':

  import argparse, os, sys, json

  parser = argparse.ArgumentParser(prog=sys.argv[0],
    description='Add *_LLDP_TX_VID/PRIO options to the WRS configuration file')
  parser.add_argument('config_file', help='path to configuration file')
  parser.add_argument('vid_file', help='path to vid file')

  # command options
  opts = parser.parse_args(sys.argv[1:])

  # path to the WRS configuration file
  config_path = os.path.abspath(opts.config_file)
  vid_path = os.path.abspath(opts.vid_file)

  # get lldp vid
  lldp_vid = ''
  with open(vid_path, 'r') as f:
    lldp_vid = json.load(f)['lldp']

  # update file
  apply_inplace(config_path, lldp_vid)

