# home-infra

An Ansible playbook that sets up multiple Debian servers with Proxmox and some hardening.

## Pre-requisites:
* Ansible control node with ansible-core available
* All controlled nodes assume a standard Debian installation that was configured using ps.cfg from ./debian-preseed

## Sensitive info:
* Configure your editor by exporting EDITOR=nano in your .bashrc
* Configure your vault password by setting it in .vault_pass
* Point to this file in your ansible.cfg, by setting "vault_password_file = .vault_pass" in the [defaults]-section
* To keep it out of this repository, I have configured ansible.cfg to point to your home folder. Create the .vault_pass there.
* Run the following commands from the directory where ansible.cfg is residing, or else it will not pick up the location of .vault_pass
* Set your sensitive info by running: ansible-vault encrypt_string 'some_sensitive_value' --name 'variable_containing_sensitive_stuff'
* In case of a password - the "some_sensitive_value" should already be hashed with mkpasswd -m sha-512
* E.g.: ansible-vault encrypt_string 'SuperSecretPassword' --name 'root_pass'. The resulting string will be able to be used in your .yaml 


## Services included:
* [Proxmox]
* [log2ram]
* [Samba Active Directory Domain Controller]

## Role-common:
* Sets force-colors in .bashrc
* Edits journald to reduce journal sizes. Also vacuums to 10M
* Sets IPv6 to not autoconfigure
* Sets hostname and changes /etc/hosts to reflect
* Removes the has_journal flag from the root filesystem. Also sets noatime,nodiratime
* Adds passwordless sudo for members of the sudo group
* Installs powertop and sets powertop --auto-tune to run at startup

## Role-log2ram:
* Installs log2ram - moves /var/log to a memory-based disk

## Role-pve:
* Follows https://pve.proxmox.com/wiki/Install_Proxmox_VE_on_Debian_12_Bookworm to install pve over the standard Debian install
* Also sets root user password for initial login into web-interfaceset

## Role-pxe-prep:
* Overwrites the MBR on the /dev/sda. This will prompt a PXE-based boot next restart.
* Set "-e pve_reset=true" on the command-line

## Role samba-ad-dc:
* Follows https://waal70blog.wordpress.com/2017/05/01/raspberry-pi-as-a-domain-controller/ for provisioning of a domain
* Follows https://waal70blog.wordpress.com/2017/12/03/joining-a-secondary-raspberry-pi-to-your-domain/ for additional domain controllers
* Follows https://waal70blog.wordpress.com/2017/12/03/setting-up-sysvol-replication/ for the SysVol replication
* Yes, these are also shameless plugs :)

## To use preseed:
* Publish ./debian-preseed/preseed.cfg on a webserver
* On the installer, go to the HELP option
* At the boot: prompt, type: auto url=http://webserver/preseed.cfg" there, replacing webserver with the address to your webserver that is hosting ps.cfg
* If your client has internet connectivity, you could even refer it to: https://raw.githubusercontent.com/waal70/home-infra/main/debian-preseed/preseed.cfg 
* Hint for myself: adpi0 has a preseed.cfg at the root :)

## PXE-boot:
* See ./debian-preseed/tftp-HOWTO.md

## To run the playbook: try this:
ansible-playbook -i inventory/hosts playbook.yml -kK

- Runs the playbook with the inventory file from the repo, asks for SSH and become passwords

## TO DO:
* ~~FIX: Ansible master now requires an earlier ssh connection, in order to save fingerprint - should be not necessary~~
* TODO: Networking is left on DHCP - change to static config
* TODO: server_hardening role is not used now
* ~~FIX: setting ^has_journal is hit and miss - does not seem to work all the time - fix this!~~
