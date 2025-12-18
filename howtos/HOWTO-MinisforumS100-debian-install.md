# Guide for booting/converting Minisforum S100 to boot Linux (Debian)

The problem is the S100 utilizes a Universal Flash Storage (UFS) device as its main storage.
Currently (trixie), the Debian installer does not include support for UFS in the (text-based) installer.
There is a workaround, however!

## Preparations

* Prepare a bootable USB stick that will write the Debian installer image.
* Be sure to include a writeable part (maybe use Rufus to create said USB stick).

* Note the exact version of the kernel that is included in the installer image.
* From an existing install (or from any repository), grab the UFS modules, replacing the version with your exact version:

```bash
./usr/lib/modules/6.12.48+deb13-amd64/kernel/fs/ufs/ufs.ko.xz
./usr/lib/modules/6.12.48+deb13-amd64/kernel/drivers/ufs/core/ufshcd-core.ko.xz
./usr/lib/modules/6.12.48+deb13-amd64/kernel/drivers/ufs/host/ufshcd-pci.ko.xz
./usr/lib/modules/6.12.43+deb13-amd64/kernel/fs/ufs/ufs.ko.xz
```

* Copy these to the writable part of your installation media.
* Proceed with installation of the S100 using your prepared medium.
* Do not choose automated install, but rather "install"
* When the partitioner shows you only the USB device, ESCape out and choose 'Open a shell'
* There, go to the modules you grabbed earlier and modprobe them into the installation (using -f to force)

```bash
modprobe -f ./<module-name1>
modprobe -f ./<module-name2>
modprobe -f ./<module-name3>
modprobe -f ./<module-name4>
```

* By typing ```exit``` you will return to the installer
* Continue the install process from the step 'detect disks'
* Installation should now continue, allowing you to select the UFS for system installation
