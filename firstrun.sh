#!/bin/bash
export PRIVATE_REPO=../home
export SSH_ASKPASS=${PRIVATE_REPO}/ssh-keys/passphrase
export SSH_ASKPASS_REQUIRE=force
ssh-agent bash
ssh-add ${PRIVATE_REPO}/ssh-keys/ansible-key


