# Get rid of @eaDir on your Synology

Find out if your system is affected:

```bash
find /volume1/media -name "@eaDir" -type d -prune
```

Find out the space occupied by these files:

```bash
find /volume1/media -name "@eaDir" -type d -prune -mtime -1 -print0 | du --files0-from=- -hc | tail -n1
sudo find /volume1 -name "@eaDir" -type d -prune -mtime -1 -print0 | du --files0-from=- -hc | tail -n1
```

And finally, to shoot the cannon at these files:

```bash
find /volume1/torrents -name "@eaDir" -type d -prune -exec rm -rf {} \;
```
