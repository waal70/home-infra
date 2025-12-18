# HOWTO prepare your environment for network/pxe boot (Debian)

Configure the boot order of the device you would like to be able to network boot. Usually this means going into the BIOS and looking for "Boot Order":

1) Primary HD first
2) USB / Removable media second
3) NIC / PXE third

This way, on a valid install, you will always boot from the internal drive.
If this drive fails or there is another issue, it will look for a USB image, then do a PXE boot.
This order ensures you may do a manual intervention if needed by supplying a bootable USB.

## How to force PXE boot

WARNING: This will obliterate the partitions on your HDD!

This is assuming you have "classical" boot, i.e. MBR-based (also named BIOS mode or Legacy mode)
The MBR stores the bootloading instructions in the first few bits of the hard disk. Zeroing them will therefore make the device unable to boot!
You will need to find the device name of the device that holds your boot partition. You can find this (on Linux) by issuing a ```df -h``` and checking to see where the root ('/') partition is mounted.

Most likely, the device will be called ```/dev/sda1``` or ```/dev/nvme0n1p1```
Now strip off the part that contains the partion number, so ```/dev/sda1``` becomes ```/dev/sda```. This is the part you will use in the following command.

```bash
dd if=/dev/zero of=/dev/sda bs=446 count=1
shutdown -r now
```

Now, your system will find the /dev/sda is no longer appropriate to start from, and will move down the boot prio list!
Meaning, if you do not have a USB plugged in, it will eventually end up trying a boot from the network.

## Prepare your network to supply TFTP boot instructions

First, you will need to inform all your network-clients there is such an option available. The exact way to achieve this differs per router brand, but you are looking for the DHCP-server part and you want it to specify two options:

* DHCP Option 66 or boot server: IP address of the boot server (```1.2.3.4```)
* DHCP Option 67 or bootloader path: Path to the bootloader on the boot server (```/pxelinux.0```)

On my Unifi controller these options are named and are called ```Network Boot``` and provide two input fields, one for the IP address and one for the bootloader.

Then, you will also need a boot server that actually serves the boot image. In my example, I am assuming you have a Debian machine on your network that is able to fulfill this role.
On this designated TFTP-server you will install the ```tftpd-hpa``` package. Check out the role ```waal70.tftp``` to see the details. In short: install the package (unmask, enable, restart). Usually, this has its defaults ok (/etc/default/tftpd-hpa).

Now, download netboot.tar.gz from: ```wget https://deb.debian.org/debian/dists/trixie/main/installer-amd64/current/images/netboot/netboot.tar.gz```

Place this downloaded file in your tftp folder - the one that serves boot files (e.g. /srv/tftp)

### Customize the bootloader

As the whole point is to automate your installs, it would be nice to have your options already served in the boot stage. This means providing a ```preseed.cfg```.
Here's how to inject that into your boot image:

* Unarchive the installer:

```bash
tar -xvf netboot.tar.gz
rm netboot.tar.gz
```

* OPTION ONE: You can now inject preseed.cfg right into the image:

```bash
gunzip initrd.gz
echo preseed.cfg | cpio -H newc -o -A -F initrd
gzip initrd
```

* Edit ```debian-installer/amd64/boot-screens/txt.cfg```, adding to the append-line:
```"auto=true priority=critical interface=auto"```

* OPTION TWO: Provide a preseed-url as a boot option.
* There is no archive-wrangling here, just edit the boot options in ```/debian-installer/amd64/boot-screens/txt.cfg```, adding to the append-line:
```"auto=true priority=critical interface=auto preseed/url=http://<servername-or-ip/preseed.cfg"```

* FOR BOTH OPTIONS:
* ```debian-installer/amd64/pxelinux.cfg``` is the file "default"
* Edit this to reflect a timeout value (non-zero) to autoboot (e.g. 50 for 5 seconds)
* Add a stanza to preselect ```install``` as default by adding to the end of this file:
```default install```
