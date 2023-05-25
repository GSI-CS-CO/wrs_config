#!/bin/bash

# Deploy dot-config_home* files to WRSs of the HO testbed

echo 'Deploy dot-config_home* files'

# SSH host key check disabled
SSH_OPTIONS="-n -o StrictHostKeyChecking=no"
SCP_OPTIONS="-o StrictHostKeyChecking=no"

# setups (switch_role:switch_device)
SETUP_PROD=( \
        '0298:home_access' \
        '0290:home_clockmaster' \
        '0288:home_service' \
        '0289:home_localmaster' \
        '0299:home_distribution' \
        )
SETUP_FBAS=( \
        '0298:home_fbas_access' \
        '0290:home_clockmaster' \
        '0288:home_service' \
        '0289:home_localmaster' \
        '0299:home_fbas_master' \
        )

PREFIX_DOT_CONF="dot-config"

# lookups
KEYS=('CONFIG_NTP_SERVER' \
      'CONFIG_RVLAN_RADIUS_SERVERS' \
      'CONFIG_REMOTE_SYSLOG_SERVER')

# Choose setup
echo "Testbed setups"
echo " 1 : standard production"
echo " 2 : production + fbas"
echo " - : none (exit)"
echo

unset setup
read -r -p "Choose the setup by entering the index number (1/2): " answer
case $answer in
  '1') setup=("${SETUP_PROD[@]}"); echo "Chosen: SETUP_PROD" ;;
  '2') setup=("${SETUP_FBAS[@]}"); echo "Chosen: SETUP_FBAS" ;;
  *) echo "Selection not valid. Exit"; exit 1;;
esac

for entry in ${setup[@]}; do
  echo $entry
done

DST_PATH="/wr/etc/dot-config"

# Prompt passwords for proxy and remote users
echo
read -r -s -p "Root password for login: " userpasswd
export SSHPASS=$userpasswd
echo

# deploy dot-config_home* files to the designated WRS
for entry in ${setup[@]}; do

  switch_role=${entry#*:}
  switch_idx=${entry%:*}
  login_user_host="root@nwt${switch_idx}m66.timing"
  dot_config="${PREFIX_DOT_CONF}_$switch_role"

  if [ -f $dot_config ]; then
    sshpass -e scp $dot_config $login_user_host:$DST_PATH
    if [ $? -ne 0 ]; then
      echo "FAIL: $switch_idx : $switch_role cannot be deployed!"
    else
      echo "OK: $switch_idx: $switch_role"
    fi
  else
    echo "FAIL: $dot_config not found"
  fi

done

