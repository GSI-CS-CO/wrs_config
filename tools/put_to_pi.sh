#!/bin/bash

echo 'Copy dot-config files to Pi server'

CONFIG_DIR='output/config'

# Prompt passwords for proxy and remote users
read -r -s -p "Password for pi@raspberrypi: " pi_passwd
echo

export SSHPASS=$pi_passwd

# SSH host key check disabled
SSH_OPTIONS="-n -o StrictHostKeyChecking=no"
SCP_OPTIONS="-o StrictHostKeyChecking=no"

# dot-config files
DOT_CONFIG_FILES=('dot-config_production_clockmaster' \
        'dot-config_production_service' \
        'dot-config_production_localmaster' \
        'dot-config_production_distribution' \
        'dot-config_production_access')

# remote copy of dot-config files to Pi server
for file in ${DOT_CONFIG_FILES[@]}; do

  CONFIG_FILE=$file
  TARGET_FILE=$file.lldp.vlan
  sshpass -e scp $SCP_OPTIONS $CONFIG_DIR/$CONFIG_FILE pi@raspberrypi:./$TARGET_FILE
  if [ $? -ne 0 ]; then
    echo "Copy failed with $CONFIG_FILE. Exit!"
  else
    echo "OK: copied $CONFIG_FILE as $TARGET_FILE"
  fi

done
