import sys
from argparse import ArgumentParser
import os
import re
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parameters and initial values
params = ["EGRESS_LATENCY", "INGRESS_LATENCY", "T24P_TRANS_POINT"]
port_cnt = 18
inst_cnt = 1
config_sw_ver="CONFIG_DOTCONF_FW_VERSION"

# Supported versions
valid_sw_versions=["6.1", "7.0", "8.0"]
valid_hw_versions=["3.3", "3.4"]

# Functions
def usage():
    print(f"Usage: {sys.argv[0]} -i dot-config -s wrs_sw_version -c calibration_values -t wrs_hw_version")
    print("where")
    print("  -i dot-config           configuration file")
    print(f"  -s wrs_sw_version       supported WRS software versions: {valid_sw_versions} (7.0 by default or if -s omits)")
    print("  -c calibration_values   user file with calibration values (provided 'calibration_params')")
    print(f"  -t wrs_hw_version       supported WRS hardware versions: {valid_hw_versions} (3.4 by default or if -t omits)")
    print("  -v                      verbose")
    print("  -h                      display this help and exit")

def is_file_missing(filename):
    return not filename or not os.path.isfile(filename) or os.path.isdir(filename)

def set(dotconf_file, calib_file, wrs_sw_ver="7.0", wrs_hw_ver="3.4"):
    # Check input arguments

    isCheckFailed=False
    if is_file_missing(dotconf_file):
        logger.info("Please provide input file.")
        isCheckFailed=True
    if is_file_missing(calib_file):
        logger.info("Please provide calibration file.")
        isCheckFailed=True
    if wrs_sw_ver not in valid_sw_versions:
        logger.info("Invalid version: ", wrs_sw_ver)
        logger.info(f"Supported software versions: {valid_sw_versions}")
        isCheckFailed=True
    if wrs_hw_ver not in valid_hw_versions:
        logger.info("Invalid version: ", wrs_hw_ver)
        logger.info(f"Supported hardware versions: {valid_hw_versions}")
        isCheckFailed=True

    if isCheckFailed:
        usage()
        return False

    # Load input configuration
    with open(dotconf_file, 'r') as f:
        configs = f.read()

    pattern = config_sw_ver + '="' + wrs_sw_ver + '"'
    match = re.search(pattern, configs)
    if match is None:
        logger.info(f"No match: {pattern} in {dotconf_file}")
        return False

    logger.info(f"Config file: {dotconf_file}")
    logger.info(f"Calibration file: {calib_file}")

    # Read calibration values from the given file
    calibration = {}
    with open(calib_file, 'r') as f:
        data = json.load(f);

        for item in data.get('data'):
            logger.debug(item.get('wrs_sw_ver'))
            if item.get('wrs_sw_ver') == wrs_sw_ver:    # target sw version
                for element in item.get('wrs_hw_ver'):
                    if wrs_hw_ver in element:           # target hw version
                        calibration=element.get(wrs_hw_ver)  # get the calib values
                        logger.debug(calibration)
                        break
                break

    if not calibration: # empty
        logger.info(f"Calibration values for sw={wrs_sw_ver}, hw={wrs_hw_ver}: not found! Return")
        return False
    else:
        logger.info(f"Calibration values for sw={wrs_sw_ver}, hw={wrs_hw_ver}: found.")

    # Adjust calibration values
    inst_str = f"{inst_cnt:02}"
    for port in range(1, port_cnt + 1):

        port_str = f"{port:02}"
        for i, param in enumerate(params):
            # Construct configuration parameter name
            param_name = f"CONFIG_PORT{port_str}_INST{inst_str}_{param}"
            pattern = rf"{param_name}=(\S+)"

            match = re.search(pattern, configs)
            param_act_val = match.group(1) if match else None

            # Get new value for the parameter
            key=param.split('_')[0].lower()
            if key in calibration.keys():
                arr = calibration[key]   # array of parameter values (egress, ingress or t24p)
                param_new_val = next((e.get(f"{port}") for e in arr if f"{port}" in e), None)
                logger.debug(f"{param_name} {param_act_val} : {param_new_val} (act : new)")

                # Replace actual value with new value in configs
                if param_act_val and param_name != None:
                    string_search = f"{param_name}={param_act_val}"
                    string_replace = f"{param_name}={param_new_val}"
                    configs = configs.replace(string_search, string_replace)

    # Write updated configuration to the config file
    with open(dotconf_file, 'w') as f:
        f.write(configs)

    return True

if __name__ == '__main__':

    # Parse input arguments
    parser = ArgumentParser(add_help=False)
    parser.add_argument("-i", "--input", help="Input configuration file")
    parser.add_argument("-s", "--sw_ver", default="7.0", help="Target WRS software version (default: 7.0)")
    parser.add_argument("-c", "--calibration", help="Calibration values file")
    parser.add_argument("-t", "--hw_ver", default="3.4", help="Target WRS hardware version (default: 3.4)")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="Verbosity level")
    parser.add_argument("-h", "--help", action="store_true", help="Display help and exit")
    args, unknown_args = parser.parse_known_args()

    logging.basicConfig(level=[logging.WARNING, logging.INFO, logging.DEBUG][min(args.verbosity, 2)])

    if args.help:
        usage()
        sys.exit(0)

    set(args.input, args.calibration, args.sw_ver, args.hw_ver)
