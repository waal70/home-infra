# Mount a drive that has a 'Linux raid member' partition

For reference: <https://serverfault.com/questions/383362/mount-unknown-filesystem-type-linux-raid-member>

Synology RAID1 uses the Linux RAID options. When deciding to upgrade the system, taking out the drives, or simply because
you want to do a restore yourself, you can mount the drives individually (and on another computer).
You should not mount it directly using mount. You need first to run mdadm to assemble the raid array. A command like this should do it:

(Check your device tree first if ```/dev/md0``` is available, if not, increment the number until you reach a free spot)
(Useful partition from Synology is usually 3. Check where your drive is located in the device tree and change ```/dev/sda3``` accordingly)

This also works from a SSH-shell on the Synology itself. That means you could reset the entire DiskStation, connect one of the old
RAID-members through a USB docking station and mount it to perform a 'local' restore.

```bash
sudo mdadm --assemble --run /dev/md0 /dev/sda3
```

If it refuses to run the array because it will be degraded, then you can use ```--force``` option.
When this command is executed successfully, you can mount the created device normally using:

```bash
sudo mount /dev/md0 /mnt/test
```

## Removing the array

```bash
sudo mdadm --stop /dev/md0 
```
