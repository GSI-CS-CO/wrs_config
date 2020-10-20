#!/usr/bin/env python

'''
Make WRS port-model from WRS configuration
'''
import json, re, bisect, itertools, pydot

config_file = 'dot-config'
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

    elif raw == 'n':
        return False

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

def extract_port_config(Option, port_config):

	# Insert given option to port configuration

	# Get port index from the given option
	port_idx = get_port_idx(Option.key)

	if port_idx is not None:

		port = int(port_idx)

		if port in port_config.keys():
			port_config[port][Option.key] = Option.value
		else:
			port_config[port] = {Option.key:Option.value}

def extract_vlans_config(Option, vlans_config):

	# This regex is constructed on demand
	global vlan_regex
	if vlan_regex is None:
		vlan_regex = re.compile(r'(?P<option>VLANS_VLAN(?P<vid>[0-9]+))')

	match = vlan_regex.match(Option.key)
	
	if match is not None:
		vlans_config[match.group('vid').lstrip('0')] = Option.value

def make_ranges(iterable):
	# Make iterable to range
	# iterable: sorted list (or tuple, dictionary)

	key_func = lambda pair: pair[1] - pair[0]

	for key, group in itertools.groupby(enumerate(iterable), key_func):
		group = list(group)
		if group[0][1] != group[-1][1]:
			yield group[0][1], group[-1][1]
		else:
			yield group[0][1]

def get_port_indices(raw_setting):

	# Return a list with port indices
	# raw_settings: a string with ports separated with ';'

	ids = []      # indices
	ranges = []   # ranges (indices separated with '-')

	for v in raw_setting.split(';'): # sort into indices and ranges
		if '-' in v:
			ranges.append(v)
		else:
			ids.append(v)

	# extract indices from ranges and insert them into indices list
	for r in ranges:
		lb, ub = r.split('-')
		for i in range(int(lb), int(ub) + 1):
			ids.append(str(i))

	return ids

def get_port_config(port, port_config):

	# Return port configuration relevant to timing and VLAN
	cfg_port_entries = {'name':'_IFACE', 'ptp_inst':'_INSTANCE_COUNT',
							'ptp_state':'_INST01_DESIRADE_STATE',
							'vlan_mode':'_MODE', 'vlan_vid':'_VID',
							'vlan_ptp_vid':'_PTP_VID'}
	def_port_config = {'name':'wri', 'ptp_inst':'0',
							'ptp_state':'UNKN', 'vlan_mode':'UNQL',
							'vlan_vid':'-',	'vlan_ptp_vid':'-', 'vlans':'-'}

	# update default port settings according to the given configuration
	for entry in port_config[port].keys():
		if port_config[port][entry]:
			port_idx = str(port)
			if (port_idx + cfg_port_entries['name']) in entry:
				def_port_config['name'] = port_config[port][entry]
			elif (port_idx + cfg_port_entries['ptp_inst']) in entry:
				def_port_config['ptp_inst'] = entry.split('_')[-1]
			elif (port_idx + cfg_port_entries['ptp_state']) in entry:
				def_port_config['ptp_state'] = entry.split('_')[-1]
			elif (port_idx + cfg_port_entries['vlan_mode']) in entry:
				def_port_config['vlan_mode'] = entry.split('_')[-1][:2]
			elif (port_idx + cfg_port_entries['vlan_ptp_vid']) in entry:
				def_port_config['vlan_ptp_vid'] = port_config[port][entry]
			elif (port_idx + cfg_port_entries['vlan_vid']) in entry:
				def_port_config['vlan_vid'] = port_config[port][entry]

	#print def_port_config['name'], def_port_config['ptp_inst'], def_port_config['ptp_state'], def_port_config['vlan_ptp_vid'], def_port_config['vlan_vid']

	return def_port_config

def map_vlan_to_port(vlan, ports, port_vlans):

	# Update 'port_vlans' by assigning vlan to each port

	vlan = int(vlan)

	for port in ports:
		if port in port_vlans.keys():
			# if a chosen port already exists then update its vlan list 
			vlans = port_vlans[port]
			bisect.insort(vlans, vlan) # add an element into sorted list
			port_vlans[port] = vlans
		else:
			# if a chosen port is new, create a new list with the given vlan
			port_vlans[port] = [vlan]

def get_vlans_port_list(vlan, vlans_config):

	# Return ports list assigned to the given VLAN from the provided VLANs configuration

	port_list = []

	# get the 'ports' field of each VLAN configuration: ports=1;3;5-6
	ports_field = [s for s in vlans_config[vlan].split(',') if 'ports=' in s]
	if len(ports_field):
		# get a value of the 'ports=' field
		s = ports_field[0].split('=')[-1]

		# get the port indices from the 'ports=' field
		port_list = get_port_indices(s)

	return port_list

def build_port_config_obj(port_config, vlans_config):

	# Return VLAN-relevant configurations of all ports
	# in the {port:config} format.

	port_vlans = {}      # port:vlans map
	port_config_obj = {} # port:config map

	# get timing and VLAN-relevant configurations of all ports
	for port in port_config.keys():
		port_config_obj[port] = get_port_config(port, port_config)

	#print port_config_obj
	
	# get vlans configuration
	for vlan in vlans_config.keys():
		port_list = get_vlans_port_list(vlan, vlans_config)

		# update port:[vlans] map
		if len(port_list) != 0:
			map_vlan_to_port(vlan, port_list, port_vlans)

	# extend port configuration with vlans
	for port in port_vlans.keys():
		port_vlans[port] = list(make_ranges(port_vlans[port])) # translate ports to a range for better readibility
		port_config_obj[int(port)]['vlans'] = str(port_vlans[port])

	return port_config_obj

def get_config_groups(port_config_obj):

	# Get the configuration groups from 'port_config_obj'
	r_name = {}
	r_ptp_inst = {}
	r_ptp_state = {}
	r_vlan_mode = {}
	r_vlan_vid = {}
	r_vlan_ptp_vid = {}
	r_vlans = {}
	for port, config in port_config_obj.items():
		#print('{} {}'.format(port, config))
		for k in config.keys():
			if k in 'name':
				r_name[port] = config[k]
			elif k in 'ptp_inst':
				r_ptp_inst[port] = config[k]
			elif k in 'ptp_state':
				r_ptp_state[port] = config[k]
			elif k in 'vlan_mode':
				r_vlan_mode[port] = config[k]
			elif k in 'vlan_ptp_vid':
				r_vlan_ptp_vid[port] = config[k]
			elif k in 'vlan_vid':
				r_vlan_vid[port] = config[k]
			elif k in 'vlans':
				r_vlans[port] = config[k]

	#print r_name, r_ptp_inst, r_ptp_state, r_vlan_mode, \
		r_vlan_vid, r_vlan_ptp_vid, r_vlans

	rs_name = {}
	rs_ptp_inst = {}
	rs_ptp_state = {}
	rs_vlan_mode = {}
	rs_vlan_vid = {}
	rs_vlan_ptp_vid = {}
	rs_vlans = {}

	for port in port_config_obj.keys():
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

def get_bgcolor_tag(ptp_inst, ptp_state):

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

def build_html_table(port_config_obj, wrs_name):

	# Return HTML table

	rows = get_config_groups(port_config_obj)

	line =  "<\n"
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

	# top row with port reference
	line += "          <tr>\n"
	line += "            "
	values = rows['name']
	for k in sorted(values.keys()):
		bgcolor = get_bgcolor_tag(rows['ptp_inst'][k], rows['ptp_state'][k])
		line += "<td port='" + values[k] +"t'" + bgcolor + ">" + values[k] + "</td>"
	line += "</tr>\n"

	# middle rows
	middle_row_labels = ['vlan_mode', 'vlan_ptp_vid', 'vlan_vid']
	for label in middle_row_labels:
		line += "          <tr>\n"
		line += "            "
		values = rows[label]
		for k in sorted(values.keys()):
			bgcolor = get_bgcolor_tag(rows['ptp_inst'][k], rows['ptp_state'][k])
			line += "<td" + bgcolor + ">" + values[k] + "</td>"
		line += "</tr>\n"

	# bottom row with port reference
	line += "          <tr>\n"
	line += "            "
	values = rows['vlans']
	for k in sorted(values.keys()):
		bgcolor = get_bgcolor_tag(rows['ptp_inst'][k], rows['ptp_state'][k])
		line += "<td port='" + values[k] + "b'" + bgcolor + ">" + values[k] + "</td>"
	line += "</tr>\n"

	line += "        </table>\n"
	line += "      </td>\n"

	line += "    </tr>\n"
	line += "  </table>\n"
	line += ">"

	return line

def make(config_filepath, graph_filepath):

	lines = []
	with open(config_filepath, 'r') as f:
		lines = f.readlines()

	# port and vlan configurations
	port_config = {}
	vlans_config = {}

	# {port:config} object
	port_config_obj = {}

	for line in lines:
		opt = parse_line(line[:-1]) # strip trailing new line

		if isinstance(opt, Option):
			# extract port config from option and insert it to given map
			extract_port_config(opt, port_config)

			# extract VLANs config from option and insert it to given map
			extract_vlans_config(opt, vlans_config)

	#print (json.dumps(port_config, indent=4))
	#print (json.dumps(vlans_config, indent=4))

	# build {port:config} object
	port_config_obj = build_port_config_obj(port_config, vlans_config)

	# convert to JSON
	json_obj = json.dumps(port_config_obj, indent = 2, sort_keys=True)
	#print json_obj

	wrs_name = config_filepath.partition(config_file + '_')[2]
	table = build_html_table(port_config_obj, wrs_name)

	# create an DOT graph and export to SVG format
	graph = pydot.Dot(graph_type='graph', rankdir='TB')
	wrs_model = pydot.Node(name=wrs_name, shape='plaintext', label=table)
	graph.add_node(wrs_model)

	graph.write(graph_filepath + '.dot')
	return graph.write_svg(graph_filepath + '.svg')

if __name__ == '__main__':

	import argparse, os, re, sys

	parser = argparse.ArgumentParser(prog=sys.argv[0],
		description='Get VLAN settings and save them in JSON')
	parser.add_argument('file', help='path to ' + config_file)

	# command options
	opts = parser.parse_args(sys.argv[1:])

	# path to the configuration file
	path = os.path.abspath(opts.file)

	sys.exit(make(path))
