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
sudo apt update && sudo apt install ansible
```

## Bootstrap the repositories

Install git to be able to clone the repositories. First clone the secret one, followed by the main one:


```console
git clone ssh://172.16.1.2:8022/volume1/private-git/home.git
git clone https://github.com/waal70/home-infra.git
```

Edit the ansible.cfg coming down from that main repo, so that it contains 
vault_password_file = /home/awaal/ansible/home/ansible-vault/.vault_pass

## Use ansible on itself

The target for the usage of ansible will be localhost. In order to achieve this, call the playbooks as follows:

```console
ansible-playbook --connection=local --inventory 127.0.0.1, playbook.yml
```
