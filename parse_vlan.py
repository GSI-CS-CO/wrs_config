#!/usr/bin/env python

'''
Get VLAN settings from WRS configuration file and save them in JSON.
'''
import argparse, os, re, sys, json, bisect, itertools

config_file = 'dot-config'
wrs_model_file = 'wrs.txt'
line_regex = None
port_regex = None
vlan_regex = None

class Line(object):
    pass

class Uninterpreted(Line):

    # An unknown option line in a dot-config file. It must be emitted exactly as it was seen.
    def __init__(self, content):
        self.content = content
    def __repr__(self):
        return self.content

class Option(Line):

    # A Kconfig option value or unset option
    def __init__(self, key, value):
        self.key = key
        self.value = value
    
	def __repr__(self):
		if self.value is None or (isinstance(self.value, bool) and not self.value):
			return '# CONFIG_%s is not set' % self.key
		elif isinstance(self.value, bool):
			assert self.value
			return 'CONFIG_%s=y' % self.key
		elif isinstance(self.value, int):
			return 'CONFIG_%s=%d' % (self.key, self.value)
		elif isinstance(self.value, str):
			return 'CONFIG_%s="%s"' % (self.key, self.value)
		raise NotImplementedError

def parse_value(raw):
    
    # Parse an expression that appears in the assignment of a setting ('CONFIG_FOO=%s').
    
    if raw == 'y':
        # Boolean setting that is enabled.
        return True

    elif raw.startswith('"') and raw.endswith('"'):
		# String setting.
        return raw[1:-1]

    else:
        try:
            return int(raw)
        except ValueError:
            # Something else that we don't currently support.
            raise NotImplementedError

def parse_line(line):

	# This regex is constructed on demand
	global line_regex
	if line_regex is None:
		line_regex = re.compile(r'(?P<option1>CONFIG_(?P<key1>[A-Za-z][A-Za-z0-9_]*)=(?P<value>.*))|' \
                                r'(?P<option2># CONFIG_(?P<key2>[A-Za-z][A-Za-z0-9_]*) is not set)')

	match = line_regex.match(line)

	if match is not None:

		# this line has one of option types: option1 or option2
		
		if match.group('option1') is not None:
			# a set option

			key = match.group('key1')
			raw_value = match.group('value')
			value = parse_value(raw_value)

			return Option(key, value)
		
		else:
			# an unset option

			assert match.group('option2') is not None
			key = match.group('key2')
			
			return Option(key, None)
	else:
		
		return Uninterpreted(line)

def get_port_idx(line):

	# This regex is constructed on demand
	global port_regex
	if port_regex is None:
		port_regex = re.compile(r'(?P<option>.*PORT(?P<port>[0-9]+)_.*)')

	match = port_regex.match(line)
	
	if match is not None:
		return match.group('port').lstrip('0')

	return None

def insert_port_config(Option, port_configs):

	# Insert given option to port configurations

	# Get port index from the given option
	port_idx = get_port_idx(Option.key)

	if port_idx is not None:

		port = int(port_idx)

		if port in port_configs.keys():
			port_configs[port][Option.key] = Option.value
		else:
			port_configs[port] = {Option.key:Option.value}

def insert_vlan_config(Option, vlan_configs):

	# This regex is constructed on demand
	global vlan_regex
	if vlan_regex is None:
		vlan_regex = re.compile(r'(?P<option>VLANS_VLAN(?P<vid>[0-9]+))')

	match = vlan_regex.match(Option.key)
	
	if match is not None:
		vlan_configs[match.group('vid').lstrip('0')] = Option.value

def to_ranges(iterable):
	# Return a value or range between 2 valuse
	# iterable: sorted list (or tuple, dictionary)

	key_func = lambda pair: pair[1] - pair[0]

	for key, group in itertools.groupby(enumerate(iterable), key_func):
		group = list(group)
		if group[0][1] != group[-1][1]:
			yield group[0][1], group[-1][1]
		else:
			yield group[0][1]

def parse_port_setting(raw_setting):

	# Return a list with port indices
	# raw_settings: a string with ports separated with ';'

	idxs = []      # indices
	ranges = []    # ranges (indices separated with '-')

	for v in raw_setting.split(';'): # sort into indices and ranges
		if '-' in v:
			ranges.append(v)
		else:
			idxs.append(v)

	# extract indices from ranges and insert them into indices list
	for r in ranges:
		lb, ub = r.split('-')
		for i in range(int(lb), int(ub) + 1):
			idxs.append(str(i))

	return idxs

def get_port_configs(port, port_configs):

	# Return per-port timing and VLAN-relevant configurations
	cfg_port_entries = {'name':'_IFACE', 'ptp_inst':'_INSTANCE_COUNT',
							'ptp_state':'_INST01_DESIRADE_STATE',
							'vlan_mode':'_MODE', 'vlan_vid':'_VID',
							'vlan_ptp_vid':'_PTP_VID'}
	configs = {'name':'wri', 'ptp_inst':'0',
							'ptp_state':'UNKN', 'vlan_mode':'UNQL',
							'vlan_vid':'-',	'vlan_ptp_vid':'-', 'vlans':'-'}

	# update default port settings according to the given configuration
	for entry in port_configs[port].keys():				
		if port_configs[port][entry]:
			port_idx = str(port)
			if (port_idx + cfg_port_entries['name']) in entry:
				configs['name'] = port_configs[port][entry]
			elif (port_idx + cfg_port_entries['ptp_inst']) in entry:
				configs['ptp_inst'] = entry.split('_')[-1]
			elif (port_idx + cfg_port_entries['ptp_state']) in entry:
				configs['ptp_state'] = entry.split('_')[-1]
			elif (port_idx + cfg_port_entries['vlan_mode']) in entry:
				configs['vlan_mode'] = entry.split('_')[-1][:2]
			elif (port_idx + cfg_port_entries['vlan_ptp_vid']) in entry:
				configs['vlan_ptp_vid'] = port_configs[port][entry]
			elif (port_idx + cfg_port_entries['vlan_vid']) in entry:
				configs['vlan_vid'] = port_configs[port][entry]

	#print configs['name'], configs['ptp_inst'], configs['ptp_state'], configs['vlan_ptp_vid'], configs['vlan_vid']

	return configs

def map_vlan_to_port(vlan, ports, vlans_map):

	# Update vlans_map by assigning vlan to each port in ports

	vlan = int(vlan)

	for port in ports:
		if port in vlans_map.keys():
			# if a chosen port already exists then update its vlan list 
			vlans = vlans_map[port]
			bisect.insort(vlans, vlan) # add an element into sorted list
			vlans_map[port] = vlans
		else:
			# if a chosen port is new, create a new list with the given vlan
			vlans_map[port] = [vlan]

def get_vlans_port_list(vlan, vlan_configs):

	# Return ports list of the given vlan

	port_list = []

	# get the 'ports' field of each vlan configuration: ports=1;3;5-6
	ports_field = [s for s in vlan_configs[vlan].split(',') if 'ports=' in s] 
	if len(ports_field):
		# get a value of the 'ports=' field
		s = ports_field[0].split('=')[-1]

		# parse the value of 'ports=' field into a list of ports
		port_list = parse_port_setting(s)

	return port_list

def build_port_configs_map(port_configs, vlan_configs):

	# Return VLAN-relevant configurations of all ports
  # in the {port:configs} format.

	vlans_map = {}   # port:vlans map
	configs_map = {} # port:configs map

	# get timing and VLAN-relevant configurations of all ports
	for port in port_configs.keys():			
		configs_map[port] = get_port_configs(port, port_configs)

	#print configs_map
	
	# get vlans configurations
	for vlan in vlan_configs.keys():
		port_list = get_vlans_port_list(vlan, vlan_configs)
		
		# update port:[vlans] map
		if port_list is not None:
			map_vlan_to_port(vlan, port_list, vlans_map)

	# extend port configurations with vlans
	for port in vlans_map.keys():	
		vlans_map[port] = list(to_ranges(vlans_map[port])) # translate ports to a range for better readibility
		#port_str = str(port)  # number to string conversion
		configs_map[int(port)]['vlans'] = str(vlans_map[port])

	return configs_map

def to_config_groups(port_configs_map):

	# Convert {port:configs} map into configuration groups
	r_name = {}
	r_ptp_inst = {}
	r_ptp_state = {}
	r_vlan_mode = {}
	r_vlan_vid = {}
	r_vlan_ptp_vid = {}
	r_vlans = {}
	for port, configs in port_configs_map.items():
		#print('{} {}'.format(port, configs))
		for k in configs.keys():
			if k in 'name':
				r_name[port] = configs[k]
			elif k in 'ptp_inst':
				r_ptp_inst[port] = configs[k]
			elif k in 'ptp_state':
				r_ptp_state[port] = configs[k]
			elif k in 'vlan_mode':
				r_vlan_mode[port] = configs[k]
			elif k in 'vlan_ptp_vid':
				r_vlan_ptp_vid[port] = configs[k]
			elif k in 'vlan_vid':
				r_vlan_vid[port] = configs[k]
			elif k in 'vlans':
				r_vlans[port] = configs[k]

	#print r_name, r_ptp_inst, r_ptp_state, r_vlan_mode, \
		r_vlan_vid, r_vlan_ptp_vid, r_vlans

	rs_name = {}
	rs_ptp_inst = {}
	rs_ptp_state = {}
	rs_vlan_mode = {}
	rs_vlan_vid = {}
	rs_vlan_ptp_vid = {}
	rs_vlans = {}

	for port in port_configs_map.keys():
		rs_name[port] = r_name[port]
		rs_ptp_inst[port] = r_ptp_inst[port]
		rs_ptp_state[port] = r_ptp_state[port]
		rs_vlan_mode[port] = r_vlan_mode[port]
		rs_vlan_vid[port] = r_vlan_vid[port]
		rs_vlan_ptp_vid[port] = r_vlan_ptp_vid[port]
		rs_vlans[port] = r_vlans[port]

	#print rs_name, rs_ptp_inst, rs_ptp_state, rs_vlan_mode, \
		rs_vlan_vid, rs_vlan_ptp_vid, rs_vlans

	config_groups = {}
	config_groups['name'] = rs_name
	config_groups['ptp_inst'] = rs_ptp_inst
	config_groups['ptp_state'] = rs_ptp_state
	config_groups['vlan_mode'] = rs_vlan_mode
	config_groups['vlan_ptp_vid'] = rs_vlan_ptp_vid
	config_groups['vlan_vid'] = rs_vlan_vid
	config_groups['vlans'] = rs_vlans

	#print config_groups

	return config_groups

def bgcolor_tag(ptp_inst, ptp_state):

	# Return a HTML tag used to indicate the PTP state

	ptp_master = " bgcolor='yellow'"
	ptp_slave = " bgcolor='green'"
	ptp_none = " bgcolor='orange'"
	html_tag = ''

	# PTP instance is enabled for the given port
	if ptp_inst != '0':
		if 'MASTER' in ptp_state:
			html_tag = ptp_master
		elif 'SLAVE' in ptp_state:
			html_tag = ptp_slave
		elif 'PASSIVE' in ptp_state:
			html_tag = ptp_none
	else:
		html_tag = ptp_none
	
	return html_tag

def to_table(port_configs_map, wrs_name):

	# Return HTML table

	rows = to_config_groups(port_configs_map)

	line = "[\n"
	line += "  shape=plaintext\n"
	line += "  label=<\n"
	line += "\n"
	line += "  <table border='0' cellborder='1' color='blue' cellspacing='0'>\n"
	line += "    <tr>\n"
	line += "      <td port='eth0'> " + wrs_name + "<br/>(eth0)" + "</td>\n"
	line += "      <td>\n"

	line += "        <table color='orange' cellspacing='0'>\n"
	line += "          <tr><td>port   </td></tr>\n"
	line += "          <tr><td>mode   </td></tr>\n"
	line += "          <tr><td>PTP_VID</td></tr>\n"
	line += "          <tr><td>pVID   </td></tr>\n"
	line += "          <tr><td>rVID   </td></tr>\n"
	line += "        </table>\n"
	line += "      </td>\n"

	line += "      <td>\n"
	line += "        <table color='blue' bgcolor='yellow' cellspacing='0'>\n"
	line += "          <tr>\n"
	line += "            "

	values = rows['name']
	for k in sorted(values.keys()):
		bgcolor = bgcolor_tag(rows['ptp_inst'][k], rows['ptp_state'][k])
		line += "<td port='" + values[k] +"t'" + bgcolor + ">" + values[k] + "</td>"
	line += "</tr>\n"

	line += "          <tr>\n"
	line += "            "
	values = rows['vlan_mode']
	for k in sorted(values.keys()):
		bgcolor = bgcolor_tag(rows['ptp_inst'][k], rows['ptp_state'][k])
		line += "<td" + bgcolor + ">" + values[k] + "</td>"
	line += "</tr>\n"

	line += "          <tr>\n"
	line += "            "
	values = rows['vlan_ptp_vid']
	for k in sorted(values.keys()):
		bgcolor = bgcolor_tag(rows['ptp_inst'][k], rows['ptp_state'][k])
		line += "<td" + bgcolor + ">" + values[k] + "</td>"
	line += "</tr>\n"

	line += "          <tr>\n"
	line += "            "
	values = rows['vlan_vid']
	for k in sorted(values.keys()):
		bgcolor = bgcolor_tag(rows['ptp_inst'][k], rows['ptp_state'][k])
		line += "<td" + bgcolor + ">" + values[k] + "</td>"
	line += "</tr>\n"

	line += "          <tr>\n"
	line += "            "
	values = rows['vlans']
	for k in sorted(values.keys()):
		name = rows['name'][k]
		bgcolor = bgcolor_tag(rows['ptp_inst'][k], rows['ptp_state'][k])
		line += "<td port='" + name + "b'" + bgcolor + ">" + values[k] + "</td>"
	line += "</tr>\n"

	line += "        </table>\n"
	line += "      </td>\n"

	line += "    </tr>\n"
	line += "  </table>\n"
	line += ">];"

	return line

def main(argv):
	parser = argparse.ArgumentParser(prog=argv[0],
		description='Get VLAN settings and save them in JSON')
	parser.add_argument('file', help='path to ' + config_file)
	parser.add_argument('name', help='WRS name')

	# command options
	opts = parser.parse_args(argv[1:])

	# path to the configuration file
	path = os.path.abspath(opts.file)

	# all options
	options = {}

	# port and vlan configurations
	port_configs = {}
	vlan_configs = {}

	# {port:configs} mapping
	port_configs_map = {}

	# read and parse the configuration file
	lines = []

	with open(path, 'r') as f:
		for line in f:
			line = line[:-1] # strip trailing new line
			opt = parse_line(line)
			lines.append(opt)

			if isinstance(opt, Option):
				options[opt.key] = opt

				# insert port config
				insert_port_config(opt, port_configs)

				# insert VLAN config
				insert_vlan_config(opt, vlan_configs)

	#print port_configs
	#print vlan_configs

	# build {port:configs} map
	port_configs_map = build_port_configs_map(port_configs, vlan_configs)

	# convert to JSON
	json_obj = json.dumps(port_configs_map, indent = 2, sort_keys=True)
	#print json_obj

	table = to_table(port_configs_map, opts.name)

	wrs_model_file = opts.name + ".txt"
	with open(wrs_model_file, 'w') as f: 
		f.write(table)

if __name__ == '__main__':
	sys.exit(main(sys.argv))
