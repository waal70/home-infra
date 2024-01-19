Role Name
=========

This role will turn the journaling filesystem ext4 into a non-journaling filesystem.
It does so, by removing the "has_journal" flag on the drive.
Because it affects the root filesystem, it includes some wizardry for making it so.

Requirements
------------

Debian-based. The role will figure out the device where "/" is mounted

Role Variables
--------------

None
