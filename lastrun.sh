#!/bin/bash
# Andre 09-2025: add call to script to unmount secure container:
sudo /bin/bash ${HOME}/ansible/home-infra/luks/mountContainer.sh UNDO
ssh-add -D
ssh-agent -k
unset SSH_ASKPASS_REQUIRE
unset SSH_ASKPASS
unset SSH_AGENT_PID
unset SSH_AUTH_SOCK
unset PRIVATE_REPO
