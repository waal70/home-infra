# home-infra

Forked from notthebee/infra


An Ansible playbook that sets up multiple Debian servers with Proxmox and some hardening.
Forked because I wanted a general headstart and get some ideas as to proper folder structure, etc.

It probably won't be worth the name FORK, because I will change it completely to suit my needs.

## Special thanks
* David Stephens for his [Ansible NAS](https://github.com/davestephens/ansible-nas) project. This is where I got the idea and "borrowed" a lot of concepts and implementations from.

## Services included:
* [Proxmox](https://hub.docker.com/r/homeassistant/home-assistant) 

## To use preseed:
* Publish ps.cfg on a webserver
* On the installer, go to HELP
* At the boot: prompt, type: auto url=http://webserver/path/preseed.cfg" there, replacing the URL with the address to your preseed configuration file 
* Hint: adpi0 has a ps.cfg at the root :)
