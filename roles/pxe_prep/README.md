Role Name
=========

This roles overwrites the MBR boot sector. The purpose is to render the device unbootable, prompting a
PXE boot
Specify -e "pve_reset=true" on your command-line to enable this role

It will zero out the partition that has "/" (root) mounted, and will use the device without partition number.  
So if the root filesystem is mounted on /dev/sda1, it will zero /dev/sda  

LIMITATION: if your root filesystem is mounted on a double digit partition (e.g. /dev/sda12), it will write to /dev/sda1 (in other words: it will only cut the last character)

Requirements
------------

Your system is configured to primarily boot from HDD (root_partition), followed by PXE network boot  
If the boot order is not configured in this way, your system will just hang on reboot!
