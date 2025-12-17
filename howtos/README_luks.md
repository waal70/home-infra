# My guide to setting up YubiKey for use in luks encrypted volumes

The guide will assume you have (several) Yubikey 5s, and want to satisfy the following use-cases:

* Encrypt a disk, partition or container
* Decrypt the disk with your YubiKey
* Automate the process on startup and shutdown

I also assume you are already using a Challenge-Response (HMAC-SHA1) slot on your YubiKey.
We will not initalize this, instead, we will import the existing Challenge-Response for this use.

## Prepare environment

In order for YubiKey to work with LUKS, we need to install some additional packages:

```console
sudo apt install cryptsetup yubikey-luks
```

## Identify partition, disk or container to use

Use any tool in order to designate a full disk, or create an additional partition, or even create a file
E.g. use GNOME Disks, parted, or even fdisk.
In this guide, I am assuming we will be encrypting /dev/sdc (in other words, a full disk)

### Encrypt

```console
sudo cryptsetup luksFormat /dev/sdc
```

Prompts will ask you to confirm and to set a passphrase. Use a strong passphrase. Even though we will be enrolling a Yubikey,
the passphrase will remain your fallback.

### Open

Think of a creative name that will be used as a logical way to refer to this device. I choose 'encDATA'.
The convention seems to be to choose something prefixed by 'luks'. You are the boss, you decide!

```console
sudo cryptsetup luksOpen /dev/sdc encDATA
```

This will lead to an entry under ```/dev/mapper/```, in my case not suprisingly ```/dev/mapper/encDATA```.

### Optional: use /dev/random or zero out the filesystem

This is mostly done if you use a container, for extra obfuscation. The drawback is that it can take a loooong time.

```console
sudo dd if=/dev/zero of=/dev/mapper/encDATA status=progress
```

### Create a filesystem

I will choose ext4 for this, but you are free to choose your own. Maybe you do not like journaling.

```console
sudo mkfs.ext4 /dev/mapper/encDATA
```

### Verify mapping and formatting

```console
sudo cryptsetup -v status encDATA
sudo cryptsetup luksDump /dev/sdc
```

Note that the ```luksDump``` command will also tell you about the available keyslots. 32 are available for LUKS2.

As we have just finished, chances are that only keyslot 0 is occupied (for your passphrase).

Our YubiKey will take slot 1. Remember this!

### Prepare the mountpoint and populate /etc/crypttab

This is how you will always handle mountpoints. I will choose something in my home-folder: ```mkdir ~/DATA```.
Make a note of the UUID of the device that is now of type ```crypto_LUKS```, e.g. from ```lsblk -f```. We will use the ```UUID``` to refer to this device.
It is more secure than relying on sdX names, that may change between reboots.

Add the following to ```/etc/crypttab```

```console
encDATA UUID=123454678-abcd-67ad-99a4-1234567abc    none    luks,discard
```

Add the following to your ```/etc/fstab```, taking care to adapt if you chose other filesystems

```console
/dev/mapper/encDATA     /home/<user>/DATA   ext4    rw,sync,user    0   0
```

Test mount by running ```sudo mount -a```

Initializing the mounts and volumes is done by initramfs, so we need to update it:

```console
sudo update-initramfs -c -k all
```

## Add your Yubikey

Enrolling your YubiKey is now fairly easy. Remember slot 1? That is where ```-s 1``` comes from. Make sure your YubiKey is connected and issue:

```console
sudo yubikey-luks-enroll -d /dev/sdc -s 1
```

It will ask you for a passphrase. This will only work with your Yubikey(s) and we will automate, so don't go to town.

Yubico very kindly provides us with helper scripts, which we need to add to ```crypttab```. Our entry was:

```console
encDATA UUID=123454678-abcd-67ad-99a4-1234567abc    none    luks,discard
```

which we change into:

```console
encDATA UUID=123454678-abcd-67ad-99a4-1234567abc    none    luks,discard,keyscript=/usr/share/yubikey-luks/ykluks-keyscript,initramfs
```

Followed by a ```sudo update-initramfs -c -k all``` to persist the changes.

Please not that Yubico, in later versions, modified the script to no longer allow automated challenges. That is why I replace the ```/usr/share/yubikey-luks/ykluks-keyscript``` with an older one:

```console
YUBIKEY_LUKS_SLOT=2 #Set this in case the value is missing in /etc/ykluks.cfg

. /etc/ykluks.cfg

if [ -z "$WELCOME_TEXT" ]; then
    WELCOME_TEXT="Please insert yubikey and press enter or enter a valid passphrase"
fi

message()
{
    if [ -x /bin/plymouth ] && plymouth --ping; then
        plymouth message --text="$*"
    else
        echo "$@" >&2
    fi
    return 0
}

check_yubikey_present="$(ykinfo -q -"$YUBIKEY_LUKS_SLOT")"

if [ -z "$YUBIKEY_CHALLENGE" ] || [ "$check_yubikey_present" != "1" ] ; then
  if [ -z "$cryptkeyscript" ]; then
      if [ -x /bin/plymouth ] && plymouth --ping; then
          cryptkeyscript="plymouth ask-for-password --prompt"
      else
          cryptkeyscript="/lib/cryptsetup/askpass"
      fi
  fi
  PW="$($cryptkeyscript "$WELCOME_TEXT")"
else
  PW="$YUBIKEY_CHALLENGE"
fi

if [ "$check_yubikey_present" = "1" ]; then
    message "Accessing yubikey..."
    if [ "$HASH" = "1" ]; then
        PW=$(printf %s "$PW" | sha256sum | awk '{print $1}')
    fi
    R="$(printf %s "$PW" | ykchalresp -"$YUBIKEY_LUKS_SLOT" -i- 2>/dev/null || true)"
    if [ "$R" ]; then
        message "Retrieved the response from the Yubikey"
        if [ "$CONCATENATE" = "1" ]; then
            printf '%s' "$PW$R"
        else
            printf '%s' "$R"
        fi
    else
        message "Failed to retrieve the response from the Yubikey"
    fi
else
        printf '%s' "$PW"
fi

exit 0
```
