'''
Add the new configuration item CONFIG_ETH0_DHCP_ONCE_RETRY_N

This item is an extention to CONFIG_ETH0_DHCP_ONCE.
'''

import fileinput

def apply_inplace(filename):

    # text lines (to be sought and added)
    seek_line = "CONFIG_ETH0_DHCP_ONCE=y"
    new_line  = "CONFIG_ETH0_DHCP_ONCE_RETRY_N=10"

    # simple sed-like replacement
    for line in fileinput.input([filename], inplace=True):
        print(line, end="")
        if line == seek_line + '\n':
            print(new_line)

if __name__ == '__main__':
    import argparse, os, sys

    parser = argparse.ArgumentParser(prog=sys.argv[0],
                                     description='Add CONFIG_ETH0_DHCP_ONCE_RETRY_N=10 option to dot-config')
    parser.add_argument('config_file', help='path to dot-config')

    # command options
    opts = parser.parse_args(sys.argv[1:])

    # path to dot-config
    dot_config_path = os.path.abspath(opts.config_file)

    # apply patch
    apply_inplace(dot_config_path)
