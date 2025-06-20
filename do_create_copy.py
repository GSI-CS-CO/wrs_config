# Create the dot-config files for the HW v3.5 (by default, copy files for HW v3.4)

from argparse import ArgumentParser
import os
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supported versions
src_hw_version = "3.4"
dst_hw_version = "3.5"

# Functions
def do_copies(args):
    logger.info(f"Start copy files: {args}")

    # Get all filenames in specified directory
    abs_path=os.path.abspath(args.cfg_directory)
    dotconfig_files=[f for f in os.listdir(abs_path) if os.path.isfile(os.path.join(abs_path, f))]

    # for all dot-config files (3.x)
    # - find a source dot-config
    # - copy and rename it to desired destination dot-config

    for src_name in dotconfig_files:

        if src_hw_version in src_name:    # version match

            # destination filename
            dst_name = re.sub(src_hw_version, dst_hw_version, src_name, count = 1)

            # absolute filepaths
            abs_src_path = os.path.abspath(os.path.join(args.cfg_directory, src_name))
            abs_dst_path = os.path.abspath(os.path.join(args.cfg_directory, dst_name))

            logger.debug(f"{abs_src_path} : {abs_dst_path}")

            # copy in binary mode (recommended for general file copying)
            with open(abs_src_path, 'rb') as src_file:
                with open(abs_dst_path, 'wb') as dst_file:
                    for chunk in iter(lambda: src_file.read(4096), b''):
                        dst_file.write(chunk)

if __name__ == '__main__':

    # Parse input arguments
    parser = ArgumentParser()
    parser.add_argument("-d", "--cfg_directory", default='output/config', help="Directory with configuration files")
    parser.add_argument("-w", "--hw_ver", default='3.4', help="Source HW version")
    parser.add_argument("-v", "--verbosity", action="count", default=0, help="Verbosity level")
    args, unknown_args = parser.parse_known_args()

    logging.basicConfig(level=[logging.WARNING, logging.INFO, logging.DEBUG][min(args.verbosity, 2)])

    do_copies(args)
