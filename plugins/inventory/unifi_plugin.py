'''Unifi inventory plugin for Ansible - combines Unifi controller data with JSON topology file'''
import json
import os
import urllib3
import jmespath
import requests

# The imports below are the ones required for an Ansible plugin
from ansible.errors import AnsibleParserError
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

DOCUMENTATION = r'''
    name: unifi_plugin
    plugin_type: inventory
    short_description: Returns a dynamic host inventory from unifi controller
    description: Returns a dynamic host inventory from unifi, combined with a user-provided json file containing ansible config
    options:
      plugin:
          description: Name of the plugin
          required: true
          choices: ['unifi_plugin']
      controller_api:
        description: url of the unifi controller
        required: true
      controller_login:
        description: url to login. this is sometimes different from the api url
        required: true
      controller_site:
        description: the site identifier
        required: false
      macfile:
        description: the JSON file that contains your topology
        required: true
      vault_controller_username:
        description: the vaulted username for unifi
        required: true
      vault_controller_password:
        description: the vaulted password for the username
        required: true
'''
class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):
    """Required class for an Ansible inventory plugin."""

    NAME = 'unifi_plugin'

    def __init__(self):
        super(InventoryModule, self).__init__()
        self.plugin = None
        self.username = None
        self.password = None
        self.controller_login = None
        self.controller_api = None
        self.controller_site = None
        self.macfile = None
        self.macs: any
        self.active_clients: any
        self.headers: str
        self.str_macfile: str

        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def verify_file(self, path: str):
        if super(InventoryModule, self).verify_file(path):
            return path.endswith('unifi.yaml') or path.endswith('unifi.yml')
        return False

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)  # This also loads the cache
        try:
            self.plugin = self.get_option('plugin')
            self.username = self.get_option('vault_controller_username')
            self.password = self.get_option('vault_controller_password')
            self.controller_login = self.get_option('controller_login')
            self.controller_api = self.get_option('controller_api')
            self.controller_site = self.get_option('controller_site')
            self.macfile = self.get_option('macfile')
            self.login()
            self.read_configured_mac_addresses()
            self.list_clients()
            current_working_directory = os.getcwd()
            self.display.vv("Working from directory: " + current_working_directory)
            # loop to add nested groups:
            for record in self.macs:
                if 'children' in record:
                    # This is a group of groups
                    parentgroup = str(record["group"])
                    sublist = record["children"]
                    self.inventory.add_group(parentgroup)
                    for subgroup in sublist:
                        nested_group = str(subgroup)
                        self.inventory.add_group(subgroup)
                        if not self.inventory.add_child(parentgroup, nested_group):
                            raise AnsibleParserError

            # loop to add actual hosts
            for configured_client in self.macs:
                if 'children' in configured_client:
                    continue # We have stumbled on a nested group definition, so skip
                s_configured_client_mac = configured_client["mac"].strip().lower()
                if s_configured_client_mac in str(self.active_clients):
                    s_name = configured_client["name"]
                    s_group = configured_client["group"]
                    if isinstance(s_group,list):
                        # Multiple groups defined in this tag
                        for g in s_group:
                            self.inventory.add_group(g)
                            self.inventory.add_host(s_name, g)
                        s_group = s_group[0]
                    self.display.vv("Predefined record is " + str(configured_client))
                    for active_client in self.active_clients:
                        if active_client.get("mac").strip().lower() == s_configured_client_mac:
                            # We are now sure we have a match between configured and active client
                            # active_client contains all the info from Unifi
                            self.inventory.add_group(s_group)
                            self.inventory.add_host(s_name, s_group)
                            s_ansible_host = str(active_client.get('ansible_host'))
                            self.inventory.set_variable(s_name, "ansible_host", s_ansible_host)
                            # configured_client contains all the info from the user-provided JSON file
                            # so loop through all keys in configured_client and add them as variables
                            for key in configured_client:
                                if key in ['mac', 'name', 'group']:
                                    continue
                                self.inventory.set_variable(s_name, key, configured_client[key])

        except KeyError as kerr:
            raise AnsibleParserError("Incorrect key used: ", kerr) from kerr
        except AnsibleParserError as ape:
            raise AnsibleParserError("There was an error while parsing", ape) from ape

    def login(self):
        """Function that obtains a TOKEN from Unifi controller."""
        body =  {
            'username': self.username.encode(encoding='utf-8'),
            'password': self.password.encode(encoding='utf-8'),
            'remember': 'true'
        }
        response = requests.post(self.get_option('controller_login'),
                                 data=body,verify=False, timeout=10)
        if response.status_code != 200:
            raise AnsibleParserError("Faulty values in configfile, cannot login to controller")
        self.headers = {
            'Cookie': 'TOKEN=' + response.cookies.get("TOKEN")
        }

    def read_configured_mac_addresses(self):
        """Function that reads a file containing pre-configured hardware addresses."""
        macfile = open(self.macfile, "r", encoding="utf-8")
        self.str_macfile = macfile.read()
        self.macs = json.loads(self.str_macfile)
        macfile.close()

    def list_clients(self):
        """Function that queries unifi for known active clients"""
        uri = self.controller_api + '/s/' + self.controller_site + '/stat/sta'
        response = requests.get(uri, headers=self.headers, verify=False, timeout=10)
        self.active_clients = list(jmespath.search('''data[*].
                                              {mac: mac, ansible_host: not_null(ip, last_ip), 
                                              dhcp_hostname: hostname, 
                                              unifi_name: not_null(name, hostname)oui: oui}''',
                                   response.json()))
