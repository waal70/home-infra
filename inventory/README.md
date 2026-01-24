# Inventory files

Run the playbooks from this repository by specifiying ```-i stage/dev``` or ```-i stage/prod``` to utilize the respective inventories and group_vars.

If desired, add ```inventory = stage/prod/``` to your ```ansible.cfg``` to set the default.
The default will run if you run a playbook without a ```-i``` stanza.
