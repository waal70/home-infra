#!/usr/bin/env python3

'''
Custom inventory, accepting Unifi controller and comparing it to a list of
 configured mac addresses
'''

import argparse
import json
import configparser
import requests
import jmespath
# This to suppress the InsecureRequestWarnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def jprint(obj):
    # create a formatted string of the Python JSON object
    text = json.dumps(obj, sort_keys=True, indent=4)
    print(text)

class UnifiInventory(object):

    def __init__(self):
        self.inventory = {}
        self.read_cli_args()

        self.parse_config()
        # Called with `--list`.
        if self.args.list:
            self.inventory = self.example_inventory()
        # Called with `--host [hostname]`.
        elif self.args.host:
            # Not implemented, since we return _meta info `--list`.
            self.inventory = self.empty_inventory()
        # If no groups or vars are present, return empty inventory.
        else:
            self.read_configured_mac_addresses()
            self.login()
            self.query_unifi_controller()
            self.produce_inventory()

        print(json.dumps(self.inventory));
    
  
    def parse_config(self):
        global config
        config = configparser.RawConfigParser()   
        configFilePath = r'unifi-inventory.conf'
        config.read(configFilePath);

    def read_configured_mac_addresses(self):
        macfile = open("hosts_by_mac.json", "r")
        global str_macfile
        str_macfile = macfile.read()
        global macs
        macs = json.loads(str_macfile)
        macfile.close()

    def login(self):
        global headers
        body =  {
            'username': 'user',
            'password': 'password',
            'remember': 'true'
        }
        response = requests.post(config.get('unifi', 'controller_login'), data=body,verify=False)
        headers = {
            'Cookie': 'TOKEN=' + response.cookies.get("TOKEN")
        }

    def query_unifi_controller(self):
        uri = config.get('unifi', 'controller_api') + '/s/' + config.get('unifi', 'controller_site') + '/stat/sta'
        print('Going to query URL: ' + uri)
        response = requests.get(uri, headers=headers, verify=False)
        livelist = jmespath.search('data[*].{mac: mac, ansible_host: not_null(ip, last_ip), dhcp_hostname: hostname, oui: oui}', response.json())
        # Initialize the list that will contain all data on live clients that will be ansible'd
        global livelist_known
        livelist_known = []
        global unique_groups
        unique_groups = []

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
        # now add to unique groups the group from macs that has no mac, but only children
        unique_groups.append(jmespath.search('[?children].group', macs))
        print(jmespath.search('[?children].{group: group, children: children}', macs))

                
    def produce_inventory(self):
        # loop through the unique group names and add the relevant servers to it
        groupresult = {}
        for group in unique_groups:
            # create list of IPs under this group, unless this is a children group
            ips = [m["ansible_host"] for m in livelist_known if m.get("group") == group]
            if ips != []:
                groupresult = groupresult | {group: {'hosts': ips}}
            else:
                print ('[?group==\''+ str(group[0]) +'\'].children[]')
                children = jmespath.search('[?group==\''+ str(group[0]) +'\'].children[]', macs)
                print(children)
                groupresult = groupresult | {group: {'children': children } }             

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
        
        jprint(metaresult)
                
        #         "_meta": {
        # "hostvars": {
        #     "adpi0": {
        #         "ansible_host": "10.0.0.4",
        #         "enable_journaling": false,
        #         "interactive_home": "/home/awaal",
    # Example inventory for testing.
    def example_inventory(self):
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
        return {'_meta': {'hostvars': {}}}

    # Read the command line args passed to the script.
    def read_cli_args(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('--list', action = 'store_true')
        parser.add_argument('--host', action = 'store')
        self.args = parser.parse_args()

# Get the inventory.
UnifiInventory()
