#!/bin/bash
export PRIVATE_REPO=../home
export SSH_ASKPASS=${PRIVATE_REPO}/ssh-keys/ansible/passphrase
export SSH_ASKPASS_REQUIRE=force
# TODO: find a better option for this
ssh-agent bash
ssh-add ${PRIVATE_REPO}/ssh-keys/ansible/ansible-key
ssh-add ${PRIVATE_REPO}/ssh-keys/awaal/awaal-key
