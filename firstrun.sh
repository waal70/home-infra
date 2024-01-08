#!/bin/bash
export PRIVATE_REPO=../home
export SSH_ASKPASS=${PRIVATE_REPO}/ssh-keys/ansible/passphrase
export SSH_ASKPASS_REQUIRE=force
ssh-agent bash
ssh-add ${PRIVATE_REPO}/ssh-keys/ansible/ansible-key
ssh-add ${PRIVATE_REPO}/ssh-keys/awaal/awaal-key
