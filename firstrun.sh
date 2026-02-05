#!/bin/bash

export PRIVATE_REPO=${HOME}/ansible/home

if [ ! -d "${HOME}/.ansible/roles/waal70.debian_common" ]; then
  echo "Making sure requirements are in place..."
  ansible-galaxy install -g -f -r roles/requirements.yml
fi

# For Yubikey-backed SSH keys:
# echo y | ./sign_ssh_key.sh -c ${PRIVATE_REPO}/ssh-keys/ca/ca.pub -i ansible -p ansible -v "+30m"
# For regular SSH keys:
echo y | ./sign_ssh_key.sh -c ${PRIVATE_REPO}/ssh-keys/ca/ca-ed25519 -i ansible -p ansible -v "+12h"
