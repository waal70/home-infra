# home-infra

An Ansible playbook that sets up multiple Debian servers with Proxmox and some hardening.
Relies on a standard Debian installation, that has some defaults set. These defaults can be set by running the preseed file: ps.cfg from ./debian-preseed



## Services included:
* [Proxmox]

## Role-common:
* Sets force-colors in .bashrc
* Edits journald to reduce journal sizes. Also vacuums to 10M
* Sets IPv6 to not autoconfigure
* Sets hostname and changes /etc/hosts to reflect
* Tries to remove the has_journal flag from the root filesystem. Also sets noatime,nodiratime
* Adds passwordless sudo for members of the sudo group
* Installs powertop and sets powertop --auto-tune to run at startup

## Role-log2ram:
* Installs log2ram - moves /var/log to a memory-based disk

## Role-pve:
* Follows https://pve.proxmox.com/wiki/Install_Proxmox_VE_on_Debian_12_Bookworm to install pve over the standard Debian install
* Also sets root user password for initial login into web-interfaceset

## Role samba-ad-dc:
* Installs and configures Samba Active Directory Domain Controller
* Options are primary or additional

## To use preseed:
* Publish ./debian-preseed/ps.cfg on a webserver
* On the installer, go to the HELP option
* At the boot: prompt, type: auto url=http://webserver/ps.cfg" there, replacing webserver with the address to your webserver that is hosting ps.cfg
* If your client has internet connectivity, you could even refer it to: https://raw.githubusercontent.com/waal70/home-infra/main/debian-preseed/ps.cfg 
* Hint for myself: adpi0 has a ps.cfg at the root :)

## To run the playbook: try this:
ansible-playbook -i inventory/hosts playbook.yml -kK

## TO DO:
* FIX: Ansible master now requires an earlier ssh connection, in order to save fingerprint - should be not necessary
* TODO: Networking is left on DHCP - change to static config
* TODO: server_hardening role is not used now
* FIX: setting ^has_journal is hit and miss - does not seem to work all the time - fix this!
