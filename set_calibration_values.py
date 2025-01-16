import sys
import argparse
import os
import re

# Parameters and initial values
params = ["EGRESS_LATENCY", "INGRESS_LATENCY", "T24P_TRANS_POINT"]
port_cnt = 18
inst_cnt = 1
config_sw_ver="CONFIG_DOTCONF_FW_VERSION"

# item with the calibration values
calib_values = {
    "wrs_sw_ver" : "",
    "values" : []
}

# Functions
def usage():
    print(f"Usage: {sys.argv[0]} -i dot-config -c calibration_values -t target_hw_version")
    print("where")
    print("  -i dot-config           configuration file for WRS FW v7.0")
    print("  -c calibration_values   user file with calibration values (provided 'calibration_params')")
    print("  -t target_hw_version    supported hardware versions are 3.3 and 3.4 (v3.4 by default or if -t omits)")
    print("  -h                      display this help and exit")
    sys.exit(0)

def is_file_missing(filename):
    return not filename or not os.path.isfile(filename) or os.path.isdir(filename)

def set(dotconf_file, calib_file, wrs_sw_ver, target_hw_ver="3.4"):
    # Check input arguments
    if is_file_missing(dotconf_file):
        print("Please provide input file.")
        usage()
    if is_file_missing(calib_file):
        print("Please provide calibration file.")
        usage()
    if target_hw_ver not in ["3.3", "3.4"]:
        print("Please provide proper target hardware version (3.3 or 3.4)")
        print("Invalid version: ", target_hw_ver)
        usage()

    # Load input configuration
    with open(dotconf_file, 'r') as f:
        configs = f.read()

    pattern = config_sw_ver + '="' + wrs_sw_ver + '"'
    match = re.search(pattern, configs)
    if match is None:
        return

    print(f"Config file: {dotconf_file}")
    print(f"Calibration file: {calib_file}")

    # Parse calibration values
    if calib_values['wrs_sw_ver'] != wrs_sw_ver:
        calib_values['wrs_sw_ver'] = wrs_sw_ver
        lines = []
        with open(calib_file, 'r') as f:
            for line in f:
                if not line.strip().startswith("#"):
                    lines.append(line.strip())
        calib_values['values'] = lines

    # Adjust calibration values
    inst_str = f"{inst_cnt:02}"
    for port in range(1, port_cnt + 1):
        idx = port - 1
        port_values = calib_values['values'][idx].split(':')

        port_str = f"{port:02}"
        for i, param in enumerate(params):
            # Construct configuration parameter name
            param_name = f"CONFIG_PORT{port_str}_INST{inst_str}_{param}"
            pattern = rf"{param_name}=(\S+)"

            match = re.search(pattern, configs)
            param_act_val = match.group(1) if match else None

            # Set offset based on target hardware version
            offset = i + 1 if target_hw_ver == "3.4" else i + 4

            # Get new value for the parameter
            param_new_val = port_values[offset]
            #print(f"{param_name} {param_act_val} : {param_new_val} (act : new)")

            # Replace actual value with new value in configs
            if param_act_val:
                string_search = f"{param_name}={param_act_val}"
                string_replace = f"{param_name}={param_new_val}"
                configs = configs.replace(string_search, string_replace)

    # Write updated configuration to the config file
    with open(dotconf_file, 'w') as f:
        f.write(configs)

if __name__ == '__main__':

    # Parse input arguments
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("-i", "--input", required=True, help="Input configuration file")
    parser.add_argument("-c", "--calibration", required=True, help="Calibration values file")
    parser.add_argument("-t", "--target", default="3.4", help="Target hardware version (default: 3.4)")
    parser.add_argument("-h", "--help", action="store_true", help="Display help and exit")
    args, unknown_args = parser.parse_known_args()

    if args.help:
        usage()

    set(args.input, args.calibration, "7.0", args.target)
