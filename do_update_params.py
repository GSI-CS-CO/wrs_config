from argparse import ArgumentParser
import set_wrsauxclk_params
import logging
import os
import re
import fileinput  # perform the in-place file editing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def do_update(args):
    logger.info(f"Let's start update: {args}")

    search_fw_ver="CONFIG_DOTCONF_FW_VERSION="
    search_hw_ver="CONFIG_DOTCONF_HW_VERSION="

    # Get all filenames in specified directory
    abs_path=os.path.abspath(args.cfg_directory)
    dotconfig_files=[f for f in os.listdir(abs_path) if os.path.isfile(os.path.join(abs_path, f))]

    # for all dot-config files (3.x)
    # - update the calibration values
    for f in dotconfig_files:

        wrs_fw_ver=""
        wrs_hw_ver=""

        full_filepath=os.path.join(abs_path, f)

        with open(full_filepath, "r") as dot_config:
            lines = dot_config.readlines()
            for line in lines:
                if line.find(search_fw_ver) != -1:
                    wrs_fw_ver = line.replace(search_fw_ver, "").strip().strip('"')
                if line.find(search_hw_ver) != -1:
                    wrs_hw_ver = line.replace(search_hw_ver, "").strip().strip('"')
                if wrs_fw_ver != "" and wrs_hw_ver != "":
                    break

        # apply wrsauxclk parameters (only for valid fw/hw versions)
        if wrs_fw_ver in set_wrsauxclk_params.valid_sw_versions and \
            wrs_hw_ver in set_wrsauxclk_params.valid_hw_versions:
            set_wrsauxclk_params.set(full_filepath, args.wrsauxclk_filepath, wrs_fw_ver, wrs_hw_ver)
        else:
            logger.info(f"Invalid versions: fw={wrs_fw_ver}, hw={wrs_hw_ver}")
            continue

if __name__ == '__main__':

    # Parse input arguments
    parser = ArgumentParser()
    parser.add_argument("-d", "--cfg_directory", default='output/config', help="Directory with configuration files")
    parser.add_argument("-a", "--wrsauxclk_filepath", default='wrsauxclk_params.json', help="JSON file with wrsauxclk parameters values")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="Verbosity level")
    args, unknown_args = parser.parse_known_args()

    logging.basicConfig(level=[logging.WARNING, logging.INFO, logging.DEBUG][min(args.verbosity, 2)])

    do_update(args)