# Example yml to use proxmox inventory plugin

```yaml
plugin: "community.proxmox.proxmox"
url: https://<your-proxmox-ip>:8006/
user: root@pam
token_id: <tokenname>
token_secret: <secrethere>
want_facts: true
keyed_groups:
  - key: proxmox_tags_parsed
    separator: ""
want_proxmox_nodes_ansible_host: true
compose:
  ansible_host: (proxmox_agent_interfaces | last)['ip-addresses'] | first | split('/') | first
validate_certs: false
```
