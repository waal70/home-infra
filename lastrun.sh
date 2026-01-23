#!/bin/bash
# Andre 09-2025: add call to script to unmount secure container:
# sudo /bin/bash ${HOME}/ansible/home-infra/luks/mountContainer.sh UNDO
ansible pi5-01 -m community.general.shutdown -u ansible --become
ansible pi5-03 -m community.general.shutdown -u ansible --become
ssh-add -D
ssh-agent -k
unset SSH_ASKPASS_REQUIRE
unset SSH_ASKPASS
unset SSH_AGENT_PID
unset SSH_AUTH_SOCK
unset PRIVATE_REPO
