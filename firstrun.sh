#!/bin/bash
export PRIVATE_REPO=../home
export SSH_ASKPASS=${PRIVATE_REPO}/ssh-keys/passphrase
export SSH_ASKPASS_REQUIRE=force
# Andre fix 01/2024: from git other properties are set
chmod 0600 ${PRIVATE_REPO}/ssh-keys/ansible-key
ssh-agent bash
ssh-add ${PRIVATE_REPO}/ssh-keys/ansible-key


