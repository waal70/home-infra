# home-infra

Multiple Ansible playbooks that sets up an infrastructure. Mostly based on raspberry pi's, debian (bookworm and trixie), docker and Proxmox.

It includes an inventory-plugin that uses the UniFi ecosystem, but you can also use non-dynamic inventory.
  
## Pre-requisites
  
* Ansible control node with ansible-core available (for some nice chicken-egg there is the role ```waal70.ansible_control``` included)
* All controlled nodes assume a standard Debian installation that was configured using preseed.cfg from the role ```waal70.tftp```
* This set of files assumes two named users, you will need to generate SSH keypairs for both:
  * one that is the user that ansible will run under. You may refer to this in playbooks as ```ansible_user```
  * one that is the user a human may use to login to ansible-controlled nodes. You may refer to this in your playbooks as ```interactive_user```
* For want of a better solution, this also requires the existence of a ```PRIVATE_REPO```. In my case it is a self-hosted git-repository. In this repository, among other things, the SSH-keys for the two named users are stored. The layout of that repository is as follows:

```bash
PRIVATE_REPO
├── ansible-vault
│   ├── ansible-galaxy-api-token
│   ├── .vault_pass
│   └── <FQ-rolename>-vars.yml
├── homepage
│   ├── bookmarks.yaml
│   ├── custom.css
│   ├── custom.js
│   ├── docker.yaml
│   ├── kubernetes.yaml
│   ├── proxmox.yaml
│   ├── services.yaml
│   ├── settings.yaml
│   └── widgets.yaml
├── inventory
│   ├── hosts_by_mac.json
│   ├── inv_unifi.yml
├── ssh-keys
│   ├── <ansible_user>
│   │   ├── <ansible_user>-key
│   │   ├── <ansible_user>-key.pub
│   │   └── passphrase
│   ├── <interactive_user>
│   │   ├── <interactive_user>-yubi-1
│   │   ├── <interactive_user>-yubi-1.pub
│   │   ├── <interactive_user>-yubi-2
│   │   ├── <interactive_user>-yubi-2.pub
│   │   └── config
```

## Dealing with sensitive info
  
* Configure your vault password by setting it in ```.vault_pass```. Mine is stored in my private repo under ```ansible-vault```, as you can see above
* Point to this file in your ```ansible.cfg```, by setting ```vault_password_file = .vault_pass``` in the ```[defaults]```-section, of course specifying the proper path to the private repository
* Remember to subsequently run all commands from the directory where ansible.cfg is residing, or else it will not pick up the correct configuration
* The command to encrypt sensitive info is: ```ansible-vault encrypt_string 'some_sensitive_value' --name 'variable_containing_sensitive_stuff'```
* In case of a password - the "some_sensitive_value" should already be hashed with ```mkpasswd -m sha-512```

Example:

```bash
ansible-vault encrypt_string 'SuperSecretPassword' --name 'root_pass'
```

Depending on your .vault_pass, this will yield:

```bash
Encryption successful
root_pass: !vault |
          $ANSIBLE_VAULT;1.1;AES256
          38633730386435346138626532316130653339653031613233343533336135333132396165633736
          3962643565633164303435363235326162346563313564650a323032383634396336663461623034
          35376638303236636636616362303736653637313063353831613536386635383963636239306439
          6665643262383639650a346435326531363964376463663639653962383932613264366430636630
          34346639356365343462613434626261373430326566656433316435383563643762
```

The variable definition string can be used in a yaml.

* I protect my SSH-keys with a passphrase. You will need to run an agent and add the keys to that if you wish to not type the private key's passphrase all the time. I have included ```firstrun.sh``` to show you how to do it.

### LUKS

For an extra layer of security in using a private repository, I also decided to only git clone the private repository into a LUKS-encrypted container. Please see ```luks/mountContainer.sh``` to see how I achieved this.

## Inventory

My setup has Unifi-based networking, it is SDN-like and employs a controller. This means that central info on IP-addresses and connected clients is maintained by the Unifi controller.
This is why I choose to (dynamically) retrieve IP-addresses for hosts I would like to manage with Ansible from that controller. The key for that is the MAC-address. If you would like to use this as well, you may use the inventory-plugin from this repository, ```unifi_plugin.py```. This plugin requires the existence of a ```inv_unifi.yml```. An example is inside the ```inventory``` folder, but you use ```ansible.cfg``` to point to its forever home. In my case, you guessed it, it is in the private repository.
This file configures the settings for the Unifi-controller, such as the URLs for the API, the credentials, and the site you would like to target (in case of multiple sites). It also has an entry for ```macfile```. This should point to a JSON-file that contains the configuration, per-client, for ansible. An example is provided inside the ```inventory``` folder (```hosts_by_mac.json```). The ```inv_unifi.yml``` allows you to put this file wherever on your filesystem. May I suggest the ```inventory``` folder in your private repo?

Of course, you may also specify a normal inventory file. Check the [Ansible documentation](https://docs.ansible.com/projects/ansible/devel/inventory_guide/intro_inventory.html) for more information on how to properly do that.

## Roles included

Well, I say "included" but in actual fact they reside in their own repositories. That is why, under the ```roles``` folder, you will find a ```requirements.yml```, listing all possible roles that are handled/used by this set of playbooks. You may manually install these roles by running:

```bash
ansible-galaxy install -g -f -r roles/requirements.yml
```

In the ```firstrun.sh```, however, there is a check included that will run this automatically, should the roles not have been found on your system.

## Bootstrapping/Terraforming/Preseeding

In order to facilitate a known good basis to build from, these playbooks all expect a certain baseline of install. All of the hosts are expected to run Debian Linux (headless). As of writing this guide, trixie is the default version, although bookworm will also work most of the time. To ensure this baseline is there, the preseeding option of the debian-installer is used.

In the role ```waal70.tftp``` a tftp-server is brought to life, using the latest images from Debian. To it, a ```preseed.cfg``` is added, so that after initial install, all hosts end up in a more or less similar state, which is well described in the documentation.

## PXE-boot

To further automate this, you should enable Network Booting or PXE Booting on the hosts that you wish to manage with Ansible. A howto is provided in the ```howtos``` folder of this repository (```tftp-HOWTO.md```)

## General instructions to run the playbook

```bash
./firstrun.sh
ansible-playbook site.yml
```

Use ```--limit inventory_name``` to limit the execution to certain hosts.
Use any of the numbered yaml-files (in ```playbooks```) to only select a portion of the roles.

## TO DO

Future plans of this repository include:

* Adding a CI/CD pipeline to automate some steps (running the playbook?) after changes are committed.
* Implementing a 'pull' mechanism so that hosts are less dependent on the ansible-controller

## License

[GPLv3](https://www.gnu.org/licenses/gpl-3.0.html#license-text)
  
## Author information

Unless otherwise noted, this entire repository is (c) 2023-2025 by André (waal70). [See github profile](https://github.com/waal70)

Please contact me if you need a commercial license for any of these files, including the ones in the ```roles/requirements.yml```
