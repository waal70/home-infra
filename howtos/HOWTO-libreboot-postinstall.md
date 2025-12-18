# Some things to do after libreboot install

System complaining about mei_me? Messages in ```dmesg``` stating that after so many restarts, the device was disabled?
It is because we have nerfed the Intel Management Engine, but Linux still inserts modules for it.

To remove the modules currently inserted:

```console
sudo rmmod mei_me
sudo rmmod mei
```

To persist this, blacklist these modules and tell the initial RAM file system that they are blacklisted:

Create a ```99-libreboot.conf``` in ```/etc/modprobe.d/```

Make its contents:

```console
blacklist mei_me
blacklist mei
```

After saving, update the initramfs by executing:

```console
sudo update-initramfs -u
```

Now, when rebooting, these messages should no longer be generated on your system!
