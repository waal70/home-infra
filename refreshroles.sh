#!/bin/bash

# First delete
/bin/bash ./deleteroles.sh

# Then run command to retrieve
ansible-galaxy install -g -f -n -r roles/requirements-local.yml
