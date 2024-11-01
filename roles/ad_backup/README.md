ad_backup
=========

This role checks the integrity of your Samba-based AD domain and will perform an online backup.  
Following the steps that are here: [https://wiki.samba.org/index.php/Back_up_and_Restoring_a_Samba_AD_DC]

It will also transfer the backup-file to the ansible controller and (optionally) put it on a network server by ephemerally mounting a samba-share

Role Variables
--------------

```python
smb_username: Administrator
smb_password: "{{ vault_smb_password }}"
backup_path: "/tmp"
backup_max_age: "30d"
smb_backup_share: "//ip-address/backup"
smb_backup_path: "/whateverfolderis/to/follow"
local_backup_path: "/mnt/backup"
cifcreds: "{{ lookup('ansible.builtin.env', 'PRIVATE_REPO') | default('~') }}/ansible-vault/.cifscredential"
vault_smb_password: yourpasswordhere
```

License
-------

MIT

Author Information
------------------

[https://github.com/waal70]