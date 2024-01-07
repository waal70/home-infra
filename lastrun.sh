#!/bin/bash
ssh-add -D
ssh-agent -k
unset SSH_ASKPASS_REQUIRE
unset SSH_ASKPASS
unset SSH_AGENT_PID
unset SSH_AUTH_SOCK
unset PRIVATE_REPO
