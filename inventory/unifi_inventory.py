#!/usr/bin/env python3

'''
Custom inventory, accepting Unifi controller and comparing it to a list of
 configured mac addresses
 Please note it expects a unifi-inventory.conf in the same folder
 It expects also hosts-by-mac.json - where you configure hosts by mac-address
'''

import os
import argparse
import json
import configparser
import requests
import jmespath

from ansible import constants as C
from ansible.cli import CLI
from ansible.parsing.dataloader import DataLoader

from ansible.utils.display import Display
# This to suppress the InsecureRequestWarnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
config = configparser.RawConfigParser()
macs: any
headers: str
str_macfile: str
livelist_known = []
unique_groups = []

def jprint(obj):
    """Function pretty printing JSON string."""
    # create a formatted string of the Python JSON object
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)

class UnifiInventory(object):
    """Class to gather Unifi controller client info and combine it into an Ansible inventory."""

    def __init__(self):
        self.username = ''
        self.password = ''
        self.inventory = {}
        self.read_cli_args()
        current_working_directory = os.getcwd()
        Display().debug("CURRENT working directory is: " + current_working_directory)

        self.parse_config()
        # Called with `--list`.
        if self.args.list:
            self.inventory = self.produce_inventory()
        # Called with `--host [hostname]`.
        elif self.args.host:
            # Not implemented, since we return _meta info `--list`.
            self.inventory = self.produce_inventory()
        # If no groups or vars are present, return empty inventory.
        else:
            self.inventory=self.produce_inventory()

        #print(json.dumps(self.inventory))
        jprint(self.inventory)

    def parse_config(self):
        """Function that reads and parses config-file."""
        config_filepath = r'./inventory/unifi_inventory.conf'
        config.read(config_filepath)

    def read_configured_mac_addresses(self):
        """Function that reads a file containing pre-configured hardware addresses."""
        macfile = open("./inventory/hosts_by_mac.json", "r", encoding="utf-8")
        global str_macfile # pylint: disable=global-statement
        str_macfile = macfile.read()
        global macs # pylint: disable=global-statement
        macs = json.loads(str_macfile)
        macfile.close()

    def get_credentials(self):
        """Function that obtains secrets for username/password from Ansible Vault."""

        cfgfile = "./roles/unifi_info/vars/main.yml"
        loader = DataLoader()
        vault_secrets = CLI.setup_vault_secrets(loader=loader,
            vault_ids=C.DEFAULT_VAULT_IDENTITY_LIST) # pylint: disable=no-member
        loader.set_vault_secrets(vault_secrets)
        data = loader.load_from_file(cfgfile)
        self.username = data["vault_controller_username"]
        self.password = data["vault_controller_password"]
        Display().debug("Succesfully retrieved username/password-combo for user " + self.username)

    def login(self):
        """Function that obtains a TOKEN from Unifi controller."""
        global headers # pylint: disable=global-statement
        if self.username=='':
            self.get_credentials()

        body =  {
            'username': self.username.encode(encoding='utf-8'),
            'password': self.password.encode(encoding='utf-8'),
            'remember': 'true'
        }
        response = requests.post(config.get('unifi', 'controller_login'),
                                 data=body,verify=False, timeout=10)
        headers = {
            'Cookie': 'TOKEN=' + response.cookies.get("TOKEN")
        }

    def query_unifi_controller(self):
        """Function that queries the unifi controller to get a list of active clients."""
        uri = (config.get('unifi', 'controller_api') +
               '/s/' + config.get('unifi', 'controller_site') + '/stat/sta')
        Display().debug('Going to query URL: ' + uri)
        response = requests.get(uri, headers=headers, verify=False, timeout=10)
        livelist = jmespath.search('''data[*].
                                   {mac: mac, ansible_host: not_null(ip, last_ip), 
                                   dhcp_hostname: hostname, oui: oui}''',
                                   response.json())
        # Initialize the list that will contain all data on live clients that will be ansible'd
        global livelist_known # pylint: disable=global-variable-not-assigned
        global unique_groups # pylint: disable=global-variable-not-assigned

        for item in livelist:
            if item.get("mac") in str_macfile:
                # Finger out the 'group' and the 'name' from the hosts_by_mac and
                # combine them into the record
                # At the same time, create a list with unique group names
                group = [m["group"] for m in macs if m.get("mac") == item["mac"]][0]
                if group not in unique_groups:
                    unique_groups.append(group)
                name = [m["name"] for m in macs if m.get("mac") == item["mac"]][0]
                comb_dict = {'group': group, 'hostname': name}
                item = item | comb_dict
                livelist_known.append(item)
        # now loop through all macs entries that have an "ansible_host"
        # SKIP the ones that were already processed
        ah_entries = jmespath.search('[?ansible_host]', macs)
        for entry in ah_entries:
            if entry.get("mac") not in livelist:
                livelist_known.append(entry)
            group_ah = entry.get("group")
            if group_ah not in unique_groups:
                unique_groups.append(group_ah)

        # now add to unique groups the group from macs that has no mac, but only children
        unique_groups.append(jmespath.search('[?children].group', macs))
        Display().debug(jmespath.search('[?children].{group: group, children: children}', macs))


    def produce_inventory(self):
        """Function that produces the Ansible inventory."""
        self.read_configured_mac_addresses()
        self.login()
        self.query_unifi_controller()
        # loop through the unique group names and add the relevant servers to it
        groupresult = {}
        for group in unique_groups:
            # create list of logical hostnames under this group, unless this is a children group
            # get from the livelist_known those entries that exist under 'group':
            hostnames = [m["hostname"] for m in livelist_known if m.get("group") == group]
            # if there are none, it is probably a meta-group (a group of groups)
            if hostnames != []:
                # append the relevant hosts to an entry for this group:
                groupresult = groupresult | {group: {'hosts': hostnames}}
            else:
                # group of groups branch. Assume there maybe more than one, so loop
                # Change: Andre 04-2024
                for curgroup in group:
                    subgroup = { curgroup : {'children': []} }
                    children = jmespath.search('[?group==\''+ str(curgroup) +'\'].children[]', macs)
                    subgroup[curgroup]["children"] += children
                    Display().debug('[?group==\''+ str(curgroup) +'\'].children[]')
                    groupresult = groupresult | subgroup

        # now create the _meta entry:
        metaresult = {
            "_meta": {
                "hostvars": {

                }
            }
        }
        for server in livelist_known:
            entry = {server["hostname"]:{}}
            entry[server["hostname"]].update({"ansible_host": server["ansible_host"]})
            metaresult["_meta"]["hostvars"].update(entry)

        Display().debug(metaresult)

        # Add the metaresult and groupresult together:
        return metaresult | groupresult

        #         "_meta": {
        # "hostvars": {
        #     "adpi0": {
        #         "ansible_host": "10.0.0.4",
        #         "enable_journaling": false,
        #         "interactive_home": "/home/awaal",
    # Example inventory for testing.
    def example_inventory(self):
        """Function that produces an example Ansible inventory. DEV only!"""
        return {
            'group': {
                'hosts': ['192.168.56.71', '192.168.56.72'],
                'vars': {
                    'ansible_user': 'vagrant',
                    'ansible_ssh_private_key_file':
                        '~/.vagrant.d/insecure_private_key',
                    'ansible_python_interpreter':
                        '/usr/bin/python3',
                    'example_variable': 'value'
                }
            },
            '_meta': {
                'hostvars': {
                    '192.168.56.71': {
                        'host_specific_var': 'foo'
                    },
                    '192.168.56.72': {
                        'host_specific_var': 'bar'
                    }
                }
            }
        }

    # Empty inventory for testing.
    def empty_inventory(self):
        """Function that produces an empty Ansible inventory. DEV only!"""
        return {'_meta': {'hostvars': {}}}

    # Read the command line args passed to the script.
    def read_cli_args(self):
        """Function that reads the command line args passed to the script."""
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action = 'store_true')
        parser.add_argument('--host', action = 'store')
        self.args = parser.parse_args()

# Get the inventory.
UnifiInventory()
