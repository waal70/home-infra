# Use signed SSH keys for your homelab

This explains how to set-up signed SSH keys in your infrastructure. For certificate backed SSH keys using YubiKey, check out the other HOWTO.
It is important you create your own CA keys, because all certificates signed by this key-pair will be accepted by your infrastructure (bar specific settings), so you will want a strictly private CA keyset.

## Create the Certificate Authority key-pair

First, we will need a public-private key combination:
```ssh-keygen -t ed25519 -f ca-homelab -N ''```
which will leave two files: ```ca-homelab``` and ```ca-homelab.pub```.

## Prepare the host for accepting keys signed by this CA

On the host that is to accept these keys, copy over the ```ca-homelab.pub```. A good location would be ```/etc/ssh/```.
Then, change the ```sshd_config``` so that it contains this stanza:
```TrustedUserCAKeys /etc/ssh/ca-homelab.pub```

Should you have more ca-keys, you can concatenate them into this file, e.g. ```cat another_key.pub >> ca-homelab.pub```
As these are public keys, this file should have 644 permission, owned by root.

Restart sshd.

## Generate client keys

Now, we will need a key-pair that is to be signed and that can be used to connect to the prepared hosts. You will need to decide on the user (identity) that will connect:

```ssh-keygen -t ed25519 -f user-key -N '' -q -C '<name of user>'```

which will also leave two files: ```user-key``` and ```user-key.pub```

## Sign the client keys with your CA

Now, we are ready to 'validate' your user-keys by signing them with the appropriate CA. An asterisk in the ```-n``` stanza will allow all users, so it is advisable to restrict this to one user-id.
The validity stanza will accept an actual datetime, but it is easier to specify by using the +-sign and a period, which will mean the validity starts now and lasts the validity-stanza period.
The example below uses one year: ```+365d```.
The extensions are there to allow PTY/TTY (Terminal) interface, as the most likely use for this key will be an interactive shell login to a remote host.

```ssh-keygen -s ca-homelab -I 'name of user' -n 'user-id of user(s)' -V '+365d' -O extension:permit-pty -O extension:permit-port-forwarding user-key.pub```

which will generate a ```user-key-cert.pub```. It is important you keep this full name, as the ```-cert.pub``` suffix will be implied when using SSH to connect later on.
You can now use this key to connect to the host:

## Use the signed key to connect

```ssh -i user-key [user@]host```
Should you have SSH-agents running, or have this host configured in your ```~/.ssh/config```, you may wish to sideline that agent and/or config:
```SSH_AUTH_SOCK= ssh -i user-key [user@]host -F none```

If you kept the ```-cert.pub```, this will find this file automatically. If not, you will need to specifiy a double ```-i```, like so:

```ssh -i user-key -i user-key-cert.pub [user@]host```
