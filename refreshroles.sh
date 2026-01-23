#!/bin/bash

# First delete
/bin/bash ./deleteroles.sh

# Then run command to retrieve
ansible-galaxy install -g -f -r roles/requirements-local.yml
