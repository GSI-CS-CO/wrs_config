# Set the wrsauxclk parameters to dot-config (HW version dependent)

import sys
from argparse import ArgumentParser
import os
import re
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Parameters and initial values
params = ["WRSAUXCLK_CSHIFT", "WRSAUXCLK_SIGDEL", "WRSAUXCLK_PPSHIFT"]
config_sw_ver="CONFIG_DOTCONF_FW_VERSION"

# Supported versions
valid_sw_versions=["8.0"]
valid_hw_versions=["3.4", "3.5", "3.6"]

# Functions
def usage():
    print(f"Usage: {sys.argv[0]} -i dot-config -s wrs_sw_version -a wrsauxclk_filepaht -t wrs_hw_version")
    print("where")
    print("  -i dot-config           configuration filepath")
    print(f"  -s wrs_sw_version       supported WRS software versions: {valid_sw_versions} (8.0 by default or if -s omits)")
    print("  -a wrsauxclk_filepath   filepath with the wrsauxclk parameters")
    print(f"  -t wrs_hw_version       supported WRS hardware versions: {valid_hw_versions} (3.4 by default or if -t omits)")
    print("  -v                      verbose")
    print("  -h                      display this help and exit")

def is_file_missing(filename):
    return not filename or not os.path.isfile(filename) or os.path.isdir(filename)

def set(dotconf_file, param_file, wrs_sw_ver="8.0", wrs_hw_ver="3.4"):
    # Check input arguments

    isCheckFailed=False
    if is_file_missing(dotconf_file):
        logger.info("Please provide input file.")
        isCheckFailed=True
    if is_file_missing(param_file):
        logger.info("Please provide wrsauxclk parameter file.")
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

    # Load input configuration (dot-config)
    with open(dotconf_file, 'r') as f:
        configs = f.read()

    pattern = config_sw_ver + '="' + wrs_sw_ver + '"'
    match = re.search(pattern, configs)
    if match is None:
        logger.info(f"No match: {pattern} in {dotconf_file}")
        return False

    logger.info(f"Configuration file: {dotconf_file}")
    logger.info(f"Parameter file: {param_file}")

    # Read parameter values from the given params file
    parameter = {}
    with open(param_file, 'r') as f:
        data = json.load(f)

        for item in data.get('data'):
            logger.debug(item.get('wrs_sw_ver'))
            if item.get('wrs_sw_ver') == wrs_sw_ver:                  # sw version match
                parameter=item.get('wrs_hw_ver', {}).get(wrs_hw_ver)  # return the parameter values for the target hw version, otherwise {}
                logger.debug(parameter)
                break

    msg_prefix = f"wrsauxclk parameters for sw={wrs_sw_ver}, hw={wrs_hw_ver}"
    if not parameter: # True for None, {}, [], '', etc
        logger.info(f"{msg_prefix}: not found! Return")
        return False

    logger.info(f"{msg_prefix}: found.")

    # Adjust wrsauxclk parameter values

    for i, key in enumerate(params):
        # Construct configuration parameter name
        param_name = f"CONFIG_{key}"
        pattern = rf'{param_name}="(-?\d+)"'  # integer value (including negative integers)

        match = re.search(pattern, configs)
        param_act_val = match.group(1) if match else None

        # Get new value for the parameter
        param_new_val = parameter.get(param_name, {})
        logger.debug(f"{param_name} = {param_act_val} : {param_new_val} (act : new)")

        # Replace the actual value with new value in dot-config
        if param_new_val and param_act_val != param_new_val:
            string_search = f'{param_name}="{param_act_val}"'
            string_replace = f'{param_name}="{param_new_val}"'
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
    parser.add_argument("-a", "--wrsauxclk_filepath", help="wrsauxclk parameter values file")
    parser.add_argument("-t", "--hw_ver", default="3.4", help="Target WRS hardware version (default: 3.4)")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="Verbosity level")
    parser.add_argument("-h", "--help", action="store_true", help="Display help and exit")
    args, unknown_args = parser.parse_known_args()

    logging.basicConfig(level=[logging.WARNING, logging.INFO, logging.DEBUG][min(args.verbosity, 2)])

    if args.help:
        usage()
        sys.exit(0)

    set(args.input, args.parameter, args.sw_ver, args.hw_ver)
