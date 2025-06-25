# Install the device that will contain ansible

For some nice bootstrapping, here are the instructions to go about configuring the ansible controller node!

## Preseed

Run the network based installation as usual. This will leave you with an almost stock Debian and the interactive and ansible user configured

## Install ansible

Pre-requisites are wget and gpg, so:

```console
sudo apt install wget gpg
```

For bookworm: UBUNTU_CODENAME should be jammy

```console
export UBUNTU_CODENAME=jammy
wget -O- "https://keyserver.ubuntu.com/pks/lookup?fingerprint=on&op=get&search=0x6125E2A8C77F2818FB7BD15B93C4A3FD7BB9C367" | sudo gpg --dearmour -o /usr/share/keyrings/ansible-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/ansible-archive-keyring.gpg] http://ppa.launchpad.net/ansible/ansible/ubuntu $UBUNTU_CODENAME main" | sudo tee /etc/apt/sources.list.d/ansible.list
sudo apt update && sudo apt install ansible ansible-lint
```

## Bootstrap the repositories

Install git to be able to clone the repositories. First clone the secret one, followed by the main one.

```console
git clone ssh://172.16.1.2:8022/volume1/private-git/home.git
git clone https://github.com/waal70/home-infra.git
```

In the private repo, chmod the ssh stuff to 600 for key material
Add +x to the passphrase file

Edit the ansible.cfg coming down from that main repo, so that it contains

```console
vault_password_file = /home/awaal/ansible/home/ansible-vault/.vault_pass
```

## Install the roles

```console
ansible-galaxy install -g -f -r roles/requirements.yml
```

## Use ansible on itself

The target for the usage of ansible will be localhost. In order to achieve this, call the playbooks as follows:

```console
ansible-playbook --connection=local --inventory 127.0.0.1, 09b-devmachine.yml --extra-vars "enable_journaling=true log2ram_state=remove enable_powersave=false"
```

Please note that especially installing the graphical desktop environment may take a looooong time

## Install the keys from the Yubikey

Go to ~/.ssh

```console
ssh-keygen -K
```

Rename the private file to username-yubi-1 for the first key, and to username-yubi-2 for the second.
These names should coincide with the configured names in SSH config (also in ~/.ssh)

And, while your at it: get the Yubico Authenticator:

```console
wget https://developers.yubico.com/yubioath-flutter/Releases/yubico-authenticator-latest-linux.tar.gz
```

## Configure SSH

Place a config in ~/.ssh so that it will know which keys to use

```console
Host github.com
 HostName github.com
 IdentityFile ~/ansible/home/ssh-keys/awaal/awaal-key

Host *
 IdentityFile ~/ansible/home/ssh-keys/awaal/awaal-yubi-1
 IdentityAgent none

 ```

## Add extensions to vscode

PlatformIO requires apt install python3-venv

Pylance
Python
Ansible
Pylint
markdownlint
JMESPath
Yaml
PlatformIO

Also, open the Command Palette (Ctrl+Shift+P) and run the Preferences: Configure Runtime Arguments command
This will open the argv.json where we add the "password-store":"gnome-libsecret"

Restart vscode and go through the authentication for github. It should now be able to interact with the keyring

And, you should now be good to go!
