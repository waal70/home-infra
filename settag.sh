#!/bin/bash

# First, set the tag variable:
TAG="v3.1.1"
TAGMESSAGE="Tagging for companion release home-infra with tag $TAG"

echo "You are about to tag all Ansible roles in ~/.ansible/roles with the tag: $TAG"
echo "Please make sure no lingering commits remain, as they will be pushed."
read -p "This will tag all repos with $TAG. Are you sure [y/n]? " -n 1 -r
echo    # (optional) move to a new line
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    [[ "$0" = "$BASH_SOURCE" ]] && exit 1 || return 1 # handle exits from shell or function but don't exit interactive shell
fi

# Set the tag on this repository:
git tag -a "$TAG" -m "$TAGMESSAGE"
retVal=$?
if [ $retVal -ne 0 ]; then
    echo "Not pushing because of error for: $(pwd -P)"
else
    # Push the tag to the remote repository
    git push origin "$TAG"
fi

# Then, iterate through each git repository in the specified directory and set the tag:
for dir in ~/.ansible/roles/*; 
do 
    cd "$dir" 
    git tag -a "$TAG" -m "$TAGMESSAGE"
    retVal=$?
    if [ $retVal -ne 0 ]; then
        echo "Not pushing because of error for: $dir"
        continue
    fi
    git push origin "$TAG"
done
