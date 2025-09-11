from argparse import ArgumentParser
import set_calibration_values
import set_wrsauxclk_params
import logging
import os
import re
import fileinput  # perform the in-place file editing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def do_conversion(args):
    logger.info(f"Let's start conversion: {args}")

    act_fw_ver='7.0'
    new_fw_ver='8.0'
    act_fw_ver_param=f'{args.fw_ver_param}="{act_fw_ver}"'
    new_fw_ver_param=f'{args.fw_ver_param}="{new_fw_ver}"'

    pattern_hw_ver=r'v3\.[3-6]\b'                          # regex pattern for versions from v3.3 to v3.6

    # Get all filenames in specified directory
    abs_path=os.path.abspath(args.cfg_directory)
    dotconfig_files=[f for f in os.listdir(abs_path) if os.path.isfile(os.path.join(abs_path, f))]

    # for all dot-config files (3.x)
    # - update the FW parameter
    # - get the HW version from each file name
    # - update the calibration values
    # - insert new configuration items (dot-config for v8.0)
    for f in dotconfig_files:

        full_filepath=os.path.join(abs_path, f)
        if not modify_param(full_filepath, act_fw_ver_param, new_fw_ver_param):
            continue                                 # ignore, if no FW parameter conversion

        version_list=re.findall(pattern_hw_ver, f)   # grab hw version

        if version_list:                             # not empty
            hw_version=version_list[-1][1:]          # clean hw version (last item in list, remove 1st char)
            success=set_calibration_values.set(full_filepath, args.calib_filepath, new_fw_ver, hw_version)

            if not success:                          # restore the old fw parameter
                modify_param(full_filepath, new_fw_ver_param, act_fw_ver_param)
                return

            # apply wrsauxclk parameters (only for valid hw versions)
            if hw_version in set_wrsauxclk_params.valid_hw_versions:
                set_wrsauxclk_params.set(full_filepath, args.wrsauxclk_filepath, new_fw_ver, hw_version)

            # insert new configuration items
            insert_config_items(full_filepath)

def modify_param(file_path, old_str, new_str) -> bool:

    isChanged = False

    if not os.path.isfile(file_path):
        logger.error(f"File {file_path} does not exist.")
        return isChanged

    for line in fileinput.input(file_path, inplace=True):
        if old_str in line:
            print(line.replace(old_str, new_str), end='') # print to stdout to modify file
            isChanged = True
        else:
            print(line, end='')

    return isChanged

def insert_config_items(file_path):

    # Read the actual configuration (from dot-config)
    with open(file_path, 'r') as f:
        configs = f.readlines()

    # insert configuration items at specific positions
    config_items={"CONFIG_NTP_SERVER": "CONFIG_TOD_SOURCE_NTP=y\n",
                  "CONFIG_SNMP_SWCORESTATUS_DISABLE": "CONFIG_SNMP_SWCORESTATUS_TX_FORWARD_DELTA=10\n"}

    # look for a specific configuration item in configurations and
    # insert new configuration item behind it
    for key, item in config_items.items():
        for idx, config in enumerate(configs):
            if key in config:
                configs.insert(idx + 1, item)
                break

    # Write updated configuration (to dot-config)
    with open(file_path, 'w') as f:
        f.write(''.join(configs))

if __name__ == '__main__':

    # Parse input arguments
    parser = ArgumentParser()
    parser.add_argument("-d", "--cfg_directory", default='output/config', help="Directory with configuration files")
    parser.add_argument("-c", "--calib_filepath", default='calibration_values.json', help="JSON file with calibration values")
    parser.add_argument("-a", "--wrsauxclk_filepath", default='wrsauxclk_params.json', help="JSON file with wrsauxclk parameters values")
    parser.add_argument("-f", "--fw_ver_param", default='CONFIG_DOTCONF_FW_VERSION', help="FW version entry in dot-config")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="Verbosity level")
    args, unknown_args = parser.parse_known_args()

    logging.basicConfig(level=[logging.WARNING, logging.INFO, logging.DEBUG][min(args.verbosity, 2)])

    do_conversion(args)