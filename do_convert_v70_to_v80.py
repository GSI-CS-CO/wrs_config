from argparse import ArgumentParser
import set_calibration_values
import logging
import os
import re

logger = logging.getLogger(__name__)

def_config_dir='output/config'
wrs_calib_filepath='calibration_values.json'
wrs_sw_version='8.0'
param_fw_version='CONFIG_DOTCONF_FW_VERSION'           # dot-config parameter for fw version
pattern_hw_ver=r'v3\.\d+\b'                            # pattern for v3.x
act_fw_ver=param_fw_version + '="7.0"'
new_fw_ver=param_fw_version + '="' + wrs_sw_version + '"'

def do_conversion(args):
    logger.info(f"Let's start conversion: {args}")

    # Get all filenames in specified directory
    abs_path=os.path.abspath(args.config_dir)
    dotconfig_files=[f for f in os.listdir(abs_path) if os.path.isfile(os.path.join(abs_path, f))]

    # for all dot-config files (3.3, 3.4)
    # - update the FW parameter
    # - get the HW version from each file name
    # - update the calibration values
    for f in dotconfig_files:

        full_filepath=os.path.join(abs_path, f)
        modify_param(full_filepath, act_fw_ver, new_fw_ver)

        version_list=re.findall(pattern_hw_ver, f)   # grab hw version

        if version_list:                             # not empty
            hw_version=version_list[-1][1:]          # clean hw version (last item in list, remove 1st char)
            success=set_calibration_values.set(full_filepath, wrs_calib_filepath, wrs_sw_version, hw_version)

            if not success:                          # restore the old fw parameter
                modify_param(full_filepath, new_fw_ver, act_fw_ver)

def modify_param(file_path, old_str, new_str):
    try:
        with open(file_path, 'r') as file:
            content = file.read()

        updated_content = content.replace(old_str, new_str)

        with open(file_path, 'w') as file:
            file.write(updated_content)

    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':

    # Parse input arguments
    parser = ArgumentParser(add_help=False)
    parser.add_argument("-c", "--config_dir", default=def_config_dir, help="Directory with configuration files")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="Verbosity level")
    parser.add_argument("-h", "--help", action="store_true", help="Display help and exit")
    args, unknown_args = parser.parse_known_args()

    logging.basicConfig(level=[logging.WARNING, logging.INFO, logging.DEBUG][min(args.verbosity, 2)])

    do_conversion(args)