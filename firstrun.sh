#!/bin/bash

# Andre 09-2025: add call to script to mount secure container:
# Moved to code.desktop file:
# Exec=gnome-terminal -- bash -c "sudo /home/awaal/ansible/home-infra/luks/mountContainer.sh && /usr/share/code/code %F"
# sudo /bin/bash ${HOME}/ansible/home-infra/luks/mountContainer.sh

export PRIVATE_REPO=${HOME}/ansible/home
export SSH_ASKPASS=${PRIVATE_REPO}/ssh-keys/ansible/passphrase
export SSH_ASKPASS_REQUIRE=force

if [ ! -d "${HOME}/.ansible/roles/waal70.debian_common" ]; then
  echo "Making sure requirements are in place..."
  ansible-galaxy install -g -f -r roles/requirements.yml
fi

ssh-agent bash
ssh-add ${PRIVATE_REPO}/ssh-keys/ansible/ansible-key
ssh-add ${PRIVATE_REPO}/ssh-keys/awaal/awaal-key
