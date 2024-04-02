Role Name
=========

This roles overwrites the MBR boot sector. The purpose is to render the device unbootable, prompting a
PXE boot
Specify -e "pve_reset=true" on your command-line to enable this role

Requirements
------------

Your system is configured to primarily boot from HDD (root_partition), followed by PXE network boot
