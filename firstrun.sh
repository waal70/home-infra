#!/bin/bash

export PRIVATE_REPO=${HOME}/ansible/home

if [ ! -d "${HOME}/.ansible/roles/waal70.debian_common" ]; then
  echo "Making sure requirements are in place..."
  ansible-galaxy install -g -f -r roles/requirements.yml
fi

./sign_ssh_key.sh -c ${PRIVATE_REPO}/ssh-keys/ca/ca-ed25519 -i ansible -p ansible -v "+10m"