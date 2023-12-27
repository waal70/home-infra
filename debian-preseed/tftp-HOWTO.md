Configure your device to a certain boot order:
* Primary HD first
* USB / Removable media seconds
* NIC / PXE third

This way, on a valid install, you will always boot from the internal drive
If this drive fails or there is another issue, it will look for a USB image, then do a PXE boot

How to force PXE boot. WARNING: This will obliterate the partitions on your HDD!~
This is assuming you have "classical" boot, i.e. MBR-based (also named BIOS mode or Legacy mode)
The MBR stores the bootloading instructions in the first few bits of the hard disk. Zeroing them will therefore be the trick:

dd if=/dev/zero of=/dev/sda bs=446 count=1

Now, your system will find the /dev/sda is no longer appropriate to start from, and will move down the boot prio list!


On your designated TFTP-server:
Download netboot.tar.gz from: wget https://deb.debian.org/debian/dists/bookworm/main/installer-amd64/current/images/netboot/netboot.tar.gz

Place this downloaded file in your tftp folder - the one that serves boot files (e.g. /srv/tftp)
The folder is configurable with your tftp server. For Debian, choose tftpd-hpa (unmask, enable, restart). Usually, this has its defaults ok (/etc/default/tftpd-hpa)

tar -xvf netboot.tar.gz
rm netboot.tar.gz

You now have two options:
OPTION ONE: Manipulate initrd.gz with a preseed.cfg file:

gunzip initrd.gz
echo preseed.cfg | cpio -H newc -o -A -F initrd
gzip initrd

in debian-installer/amd64/boot-screens/txt.cfg
add to the append-line:
"auto=true priority=critical interface=auto"

OPTION TWO: Provide preseed-url as a boot option:

Leave the folder intact, just edit the boot options in /debian-installer/amd64/boot-screens/txt.cfg:
add to the append-line:
"auto=true priority=critical interface=auto preseed/url=http://<servername-or-ip/preseed.cfg"

FOR BOTH OPTIONS:
in debian-installer/amd64/pxelinux.cfg is the file "default"
Edit to reflect a timeout value (non-zero) to autoboot (e.g. 50 for 5 seconds)
Add a stanza to preselect "install" as default by adding to the end of this file:
default install


Now, change your DHCP server to give network boot options (IP and filename). For IP, select the designated server. As filename, put /pxelinux.0
Enjoy your network boot!

To prep for ansible-user:
Using preseed/late_command:
1) Use late_command to add user 'ansible' 
1a) Use mkpasswd -m sha-512 to generate password, but it is preferred to not set a password and allow key login only
2) Be sure to escape $-characters in the generated password. Backslash is the escape-characters
3) Create the .ssh folder in the user's home
4) Add the user to the sudo group
5) Add the user's public key to the .authorized_keys file. You can generate a new key-pair with ssh-keygen
6) Set the appropriate permissions on file and folder
7) Enable passwordless sudo for this user
8) Set the appropriate permissions on the sudo entry for the user

Resulting lines command is here:
This is the line if you have a password:
# d-i preseed/late_command string in-target useradd -m -p \$6\$9xnTHkQ1U34iKGb0\$JOPr5hSM5W085TvbxH1ETdQblQS3isAIvmQun3e8qa06cFOYVAVxY6uc/bUadHAUO.02kK.ayjYyL3mWZMli.1 ansible; \
This is the line should you decide to use key login only (preferred)
d-i preseed/late_command string in-target useradd -m ansible; \
in-target mkdir -p /home/ansible/.ssh; \
in-target usermod -aG sudo ansible; \
in-target /bin/sh -c "echo 'ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQCy/RzRMaaeY2w6xtOyETFzlu3FjXHpsD6WEpo3dBXXi2FpN79RQz/ybJF3rJ1CPR0S8NXPbzWXFOf6o9bOETQDKxAQwuEa9K08o4d3aa62QheeBJWvYgOxO827mYS19u6RmsEYWDbtEqudMdDg2rKEBT/HFTf4cvphpvJSCGAkQNSjKCTx0UTqZmKxX8idDemLqxU3VT9ebmfonKQ90Xn1tq/qkZRDMf8yeL90kyHpMLZJhDT91WQvVFuA+eYCXZtIhhNMl71CfizwKHtrvvs59ej3GB29LZClaeTuSO0dBSUvK+cXNFD7JBbkZlz6MFwsl+xpPGfGHqTMIqP/1+rFzwIxJ4KfcEHy7kqH0z101oWqTHJ4QA3I7jMlgZv5kUYNji1CzVGhMM6JK1isKjiXrzQgRCqbEVSBkh0iNDMIs8jEvwOtJAb1UVDopL4gmuTEoPvhbivZxbaUC2S5EuKXZ3N30kKtUiH22DXZ58OGtFavsTyxReWkSRVB3Sm/B9U= ansible' >> /home/ansible/.ssh/authorized_keys"; \
in-target chown -R ansible:ansible /home/ansible/.ssh/; \
in-target chmod 600 /home/ansible/.ssh/authorized_keys; \
in-target chmod 700 /home/ansible/.ssh/; \
in-target /bin/sh -c "echo 'ansible ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/ansible"; \
in-target chmod 440 /etc/sudoers.d/ansible;