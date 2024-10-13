# home-infra

An Ansible playbook that sets up multiple Debian servers with Proxmox and some hardening.
It includes dynamic inventory for environments in the UniFi ecosystem, but you can also use non-dynamic inventory

## Pre-requisites

* Ansible control node with ansible-core available (for some nice chicken-egg there is the role "ansible_control" included)
* All controlled nodes assume a standard Debian installation that was configured using preseed.cfg from ./debian-preseed
* Most notably, you will need a public-private keypair for user "ansible" and store this in the...
* ...private git repository containing sensitive information (ssh-keys) named 'home' as a peer of 'home-infra'
* This repository should have ansible-vault, inventory and ssh-keys subdirectories

## Sensitive info

* Configure your vault password by setting it in .vault_pass
* Point to this file in your ansible.cfg, by setting "vault_password_file = .vault_pass" in the [defaults]-section
* To keep it out of this repository, I have configured ansible.cfg to point to a separate repository, also in your home folder. Create the .vault_pass there (i.e.: ../home)
* Run all commands from the directory where ansible.cfg is residing, or else it will not pick up the location of .vault_pass
* Set your sensitive info by running: ansible-vault encrypt_string 'some_sensitive_value' --name 'variable_containing_sensitive_stuff'
* In case of a password - the "some_sensitive_value" should already be hashed with mkpasswd -m sha-512

E.g.:

    ansible-vault encrypt_string 'SuperSecretPassword' --name 'root_pass'

The resulting string will be able to be used in your .yaml

* This playbook expects to run as user 'ansible' that has a key-pair. The public key is provided in the preseed-stage
* Expect to type the private key's passphrase a lot, unless you use ssh-agent (automated in first-run):
* ssh-agent bash
* ssh-add full-path-to-private-key

## Inventory

Either specify a regular inventory file (such as the included /inventory/hosts). Include the ansible_host in the entry,
so that a typical entry may look as follows:

    [proxmox_servers]
    pve01 ansible_host=172.16.11.108

The repository also includes a dynamic inventory, which currently is based on a UniFi environment.
It will query the Unifi-controller for a list of currently active clients. It compares this list
against a known list of mac-addresses, that you wish to configure with Ansible.
These mac-addresses are in the /inventory/hosts_by_mac.json file, you will need to specify an entry as follows:

    [
        {
        "group": "jumpservers",
        "name": "pi04",
        "mac": "b8:27:eb:d6:0c:d2"
        "otherkeysareignored": "woopwoop",
    },
    ]

The markup speaks for itself, I hope.
There are two types of special entries, the first details a group of groups, allowing nesting:

    {
        "group": "groupofgroups",
        "children": [
        "proxmox_servers",
        "other_group"
        ]
    }

The second details an entry for which you already have the IP-address (because it is maybe outside Unifi scope).
It has all the default groups, but MANDATORILY also a "hostname" entry and a "ansible_host" entry with the IP.
Later I will try and fix the doubling of hostname and name, but for now, this is what it is...

    {
        "group": "util",
        "hostname": "adpi0",
        "name": "adpi0",
        "mac": "e4:5f:01:82:c0:16",
        "ansible_host": "10.0.0.4"
    }

## Services included

* [Proxmox]
* [log2ram]
* [Samba Active Directory Domain Controller]
* Needs expanding - just doing this for the linter

## Role-common

* Sets force-colors in .bashrc (for the interactive_user)
* Edits journald to reduce journal sizes. Also vacuums to 10M
* Sets IPv6 to not autoconfigure
* Sets hostname and changes /etc/hosts to reflect
* Removes the has_journal flag from the root filesystem. Also sets noatime,nodiratime
* Adds passwordless sudo for members of the sudo group
* Installs powertop and sets powertop --auto-tune to run at startup

## Role-log2ram

* Installs log2ram - moves /var/log to a memory-based disk

## Role-pve

* Follows <https://pve.proxmox.com/wiki/Install_Proxmox_VE_on_Debian_12_Bookworm> to install pve over the standard Debian install
* Also sets root user password for initial login into web-interfaceset

## Role-pxe-prep

* Overwrites the MBR on the /dev/sda. This will prompt a PXE-based boot next restart.
* Set "-e pve_reset=true" on the command-line

## Role samba-ad-dc

* Follows <https://waal70blog.wordpress.com/2017/05/01/raspberry-pi-as-a-domain-controller/> for provisioning of a domain
* Follows <https://waal70blog.wordpress.com/2017/12/03/joining-a-secondary-raspberry-pi-to-your-domain/> for additional domain controllers
* Follows <https://waal70blog.wordpress.com/2017/12/03/setting-up-sysvol-replication/> for the SysVol replication
* Yes, these are also shameless plugs :)

## To use preseed

* Dedicate a server to the "util_server" role, which will take of all this stuff
* Change your DHCP service to provide the correct details in PXE boot stage.
* If you wish to follow along manually:
* Publish ./debian-preseed/preseed.cfg on a webserver
* Boot a target node with a Debian Install boot volume (i.e. a USB key)
* Choose "HELP" on the installer menu
* At the boot: prompt, type: auto url=<http://webserver/preseed.cfg>" there, replacing webserver with the address to your webserver that is hosting the preseed-file
* The preseed file will take care of the installer questions and leave you with a waal70 approved base image

## PXE-boot

* See ./debian-preseed/tftp-HOWTO.md
* See the details in the util_server role

## To run the playbook: try this

./firstrun.sh (to load the ssh-agent with the appropriate keys)
ansible-playbook site.yml (to kick off the full monty script)

Choose --limit inventory_name to limit the execution to certain hosts.
Choose the numbered yaml-files to only select a portion of the roles.

## TO DO

* ~~FIX: Ansible master now requires an earlier ssh connection, in order to save fingerprint - should be not necessary~~
* TODO: Networking is left on DHCP - change to static config
* TODO: server_hardening role is not used now
* ~~FIX: setting ^has_journal is hit and miss - does not seem to work all the time - fix this!~~
* Change repository adding by using the new 822 ansible task
* TODO: install default dockers on jumpserver
