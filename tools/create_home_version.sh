#!/bin/bash

# Create dot-config files for the home-office testbed

echo 'Create dot-config*.home files'

CONFIG_DIR='output/config'
IP_HOME_SERVER='192.168.2.1'

# SSH host key check disabled
SSH_OPTIONS="-n -o StrictHostKeyChecking=no"
SCP_OPTIONS="-o StrictHostKeyChecking=no"

# dot-config files
DOT_CONFIG_FILES=('dot-config_production_clockmaster' \
        'dot-config_production_service' \
        'dot-config_production_localmaster' \
        'dot-config_production_distribution' \
        'dot-config_production_access' \
        'dot-config_production_fbas_master' \
        'dot-config_production_fbas_distribution' \
        'dot-config_production_fbas_access')

# lookups
KEYS=('CONFIG_NTP_SERVER' \
      'CONFIG_RVLAN_RADIUS_SERVERS' \
      'CONFIG_REMOTE_SYSLOG_SERVER')

# create dot-config files for home-office testbed
for file in ${DOT_CONFIG_FILES[@]}; do

  # create dot-config*.home
  CONFIG_FILE_HO=$file.home
  cp $CONFIG_DIR/$file $CONFIG_DIR/$CONFIG_FILE_HO

  # search line containing the keywords and replace its non-empty value with IP_HOME_SERVER
  for keyword in ${KEYS[@]}; do
    sed -i --regexp-extended "/^$keyword/ s/=\"[0-9]+.*\"/=\"$IP_HOME_SERVER\"/" $CONFIG_DIR/$CONFIG_FILE_HO
  done

done

# Ask user to copy dot-config*.home to the remote server
read -r -p "Copy dot-config*.home to management host (Y/n): " answer
if [ "$answer" == "" ] || [ "$answer" == "Y" ] || [ "$answer" == "y" ]; then

  # Prompt user and remote host
  read -r -p "Login username and management host (ie., pi@raspberrypi): " login_user_host

  # Prompt passwords for proxy and remote users
  read -r -s -p "User password for $login_user_host: " userpasswd
  export SSHPASS=$userpasswd
  echo

else
  exit 0
fi

DST_PATH="./dot-configs/v1.5.2+fbas"
echo "dot-config*.home files will be deployed to: $DST_PATH"

# copy dot-config*.home files to the remote server
for file in ${DOT_CONFIG_FILES[@]}; do

  CONFIG_FILE_HO=$file.home

  sshpass -e scp $SCP_OPTIONS $CONFIG_DIR/$CONFIG_FILE_HO $login_user_host:$DST_PATH/$CONFIG_FILE_HO
  if [ $? -ne 0 ]; then
    echo "Copy failed with $CONFIG_FILE_HO. Exit!"
  else
    echo "OK: copied $CONFIG_FILE_HO"
  fi

done

