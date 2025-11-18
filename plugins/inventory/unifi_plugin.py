'''Unifi inventory plugin for Ansible - combines Unifi controller data with JSON topology file'''
import json
import os
from typing import List, Dict, Any, Optional
import urllib3
import requests

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
        self.plugin: Optional[str] = None
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.controller_login: Optional[str] = None
        self.controller_api: Optional[str] = None
        self.controller_site: Optional[str] = None
        self.macfile: Optional[str] = None
        self.macs: List[Dict[str, Any]] = []
        self.active_clients: List[Dict[str, Any]] = []
        self.headers: Dict[str, str] = {}
        self.session = requests.Session()

        # avoid noisy cert warnings; controller connections are often self-signed
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def verify_file(self, path: str) -> bool:
        if super(InventoryModule, self).verify_file(path):
            return path.endswith('unifi.yaml') or path.endswith('unifi.yml')
        return False

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)

        self.plugin = self.get_option('plugin')
        self.username = self.get_option('vault_controller_username')
        self.password = self.get_option('vault_controller_password')
        self.controller_login = self.get_option('controller_login')
        self.controller_api = self.get_option('controller_api')
        self.controller_site = self.get_option('controller_site') or 'default'
        self.macfile = self.get_option('macfile')

        try:
            self.login()
            self.read_configured_mac_addresses()
            self.list_clients()

            self.display.vv("Working dir: " + os.getcwd())

            # build a lookup set of active MACs for fast membership tests
            active_mac_set = {c['mac'].strip().lower() for c in self.active_clients}

            # add nested groups
            for record in self.macs:
                children = record.get('children')
                if children:
                    parentgroup = str(record.get("group"))
                    self.inventory.add_group(parentgroup)
                    for subgroup in children:
                        nested_group = str(subgroup)
                        self.inventory.add_group(nested_group)
                        if not self.inventory.add_child(parentgroup, nested_group):
                            raise AnsibleParserError(f"Failed to add child group {nested_group} to {parentgroup}")

            # add hosts and variables
            for configured in self.macs:
                if configured.get('children'):
                    continue
                mac = configured.get("mac", "").strip().lower()
                if not mac or mac not in active_mac_set:
                    continue

                name = configured.get("name")
                group = configured.get("group")
                if not name:
                    continue

                # support multiple groups
                groups = group if isinstance(group, list) else [group]
                for g in groups:
                    if g:
                        self.inventory.add_group(str(g))
                        self.inventory.add_host(name, str(g))

                # find matching active client
                match = next((c for c in self.active_clients if c.get("mac", "").strip().lower() == mac), None)
                if not match:
                    continue

                ansible_host = match.get('ansible_host')
                if ansible_host:
                    self.inventory.set_variable(name, "ansible_host", str(ansible_host))

                # set other variables from configured entry
                for key, val in configured.items():
                    if key in ('mac', 'name', 'group'):
                        continue
                    self.inventory.set_variable(name, key, val)

        except (KeyError, ValueError) as exc:
            raise AnsibleParserError(f"Parsing error: {exc}") from exc
        except AnsibleParserError:
            raise
        except Exception as exc:
            raise AnsibleParserError(f"Unexpected error: {exc}") from exc

    def login(self):
        """Obtain a session cookie/token from Unifi controller."""
        if not (self.username and self.password and self.controller_login):
            raise AnsibleParserError("Missing controller credentials or login URL")

        # post credentials; requests.Session will store cookies
        data = {
            'username': self.username.encode(encoding='utf-8'),
            'password': self.password.encode(encoding='utf-8'),
            'remember': 'true'
        }
        resp = self.session.post(self.controller_login, data=data, verify=False, timeout=10)
        try:
            resp.raise_for_status()
        except Exception as exc:
            raise AnsibleParserError(f"Failed to login to controller: {exc}") from exc

        token = resp.cookies.get("TOKEN")
        if not token:
            # some controllers may return different cookie names; store all cookies
            self.headers = {}
        else:
            self.headers = {'Cookie': f'TOKEN={token}'}

    def read_configured_mac_addresses(self):
        """Read macfile (JSON). Support relative paths safely."""
        if not self.macfile:
            raise AnsibleParserError("macfile not configured")

        path = os.path.expanduser(self.macfile)
        if not os.path.isabs(path):
            # base relative paths on inventory file dir if available
            try:
                # attempt to use inventory file path from config data
                inventory_file = self._source  # set by _read_config_data
                base = os.path.dirname(inventory_file)
            except (AttributeError, TypeError):
                base = os.getcwd()
            path = os.path.join(base, path)

        path = os.path.abspath(path)
        if not os.path.exists(path):
            raise AnsibleParserError(f"macfile not found: {path}")

        with open(path, "r", encoding="utf-8") as fh:
            try:
                self.macs = json.load(fh)
                if not isinstance(self.macs, list):
                    raise ValueError("macfile JSON root must be a list")
            except Exception as exc:
                raise AnsibleParserError(f"Failed to parse macfile {path}: {exc}") from exc

    def list_clients(self):
        """Query Unifi for active clients and normalize fields."""
        if not (self.controller_api and self.controller_site):
            raise AnsibleParserError("controller_api or controller_site not configured")

        uri = f"{self.controller_api.rstrip('/')}/s/{self.controller_site}/stat/sta"
        resp = self.session.get(uri, headers=self.headers or None, verify=False, timeout=10)
        try:
            resp.raise_for_status()
        except Exception as exc:
            raise AnsibleParserError(f"Failed to query controller API: {exc}") from exc

        payload = resp.json()
        data = payload.get('data') if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise AnsibleParserError("Unexpected API response format: 'data' missing or not a list")

        clients = []
        for item in data:
            mac = (item.get('mac') or "").strip().lower()
            if not mac:
                continue
            ansible_host = item.get('ip') or item.get('last_ip') or None
            clients.append({
                'mac': mac,
                'ansible_host': ansible_host,
                'dhcp_hostname': item.get('hostname'),
                'unifi_name': item.get('name') or item.get('hostname'),
                'oui': item.get('oui')
            })
        self.active_clients = clients
