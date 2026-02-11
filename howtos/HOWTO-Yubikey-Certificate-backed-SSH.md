# Yubikey Certificate backed SSH keys

This HOWTO will explain how to use your Yubikey to generate and sign SSH-keys.

## Pre-requisites

Ensure the ykcs11 package is installed on the system

## Enroll your first Yubikey

Verify slot 9C is empty by issuing ```ykman piv info```, there should be no entry for Slot 9C.

Create a private key by issuing ```ssh-keygen -t rsa -b 2048 -f ca-yubi -N ''```
Depending on your Yubikey's firmware, you may also opt for ed25519 type.

If you have only the one Yubikey, or you want to create a CA per Yubikey, you could use ykman also: ```ykman piv keys generate --algorithm RSA2048 9c ca-yubi.pub```
Convert the generated key into pem format: ```ssh-keygen -p -m pem -f ca-yubi```

Import the key first (not needed if the key was generated ON the Yubikey): ```ykman piv keys import 9c ca-yubi --touch-policy NEVER --pin-policy NEVER```
Then generate the certificate by issuing ```ykman piv certificates generate --hash-algorithm SHA512 -s "SSH CA Signing" -d 3650 9c ca-yubi.pub```

Retrieve the public key for this certificate:
```ssh-keygen -D /usr/lib/x86_64-linux-gnu/libykcs11.so``` (this is why you need the ykcs11-package)
Retrieve the key marked "Public Key for Digital Signature" and save it to ```ca.pub```
This ```ca.pub``` is the one you will distribute to the hosts.

## Configure the host

The ```ca.pub``` should be placed on the host. ```/etc/ssh/``` is a good location. Owned by root, chmodded to 644.
In ```sshd_config```, make sure the following stanza is present:

```TrustedUserCAKeys /etc/ssh/ca.pub```
Should you have more ca-keys, you can concatenate them into this file, e.g. ```cat another_key.pub >> ca.pub```

Restart sshd.

## Enroll your second (third, fourth...) Yubikey

Retrieve the certificate from the Yubikey you enrolled earlier:
```ykman piv certificates export 9c ca-cert.pem```

Remove the original Yubikey from USB, and insert the key you wish to enroll and issue:
For the private key import:
```ykman piv keys import 9c ca-yubi --touch-policy NEVER --pin-policy NEVER```
Then, the certificate (the --verify checks the private key matches the certificate):
```ykman piv certificates import 9c ca-cert.pem --verify```

Use ```ykman piv info``` to verify the fingerprints are the same

Slot 9C (SIGNATURE):
  Private key type: RSA2048
  Public key type:  RSA2048
  Subject DN:       CN=SSH CA Signing
  Issuer DN:        CN=SSH CA Signing
  Serial:           37:ae:86:61:65:1d:b1:20:6c:07:c6:1e:cf:bd:65:41:50:20:d2:2b
  Fingerprint:      e9522ada1e0b9e100794b60f52baf12ffcd50a93baa27bb285944a52926862dd
  Not before:       2026-02-04T11:32:51+00:00
  Not after:        2036-02-02T11:32:51+00:00

## Sign a user key with a validity of 12 hours

For this, we first need a user key-pair:
```ssh-keygen -t ed25519 -f user-key -N '' -q -C 'username'``` (yes, you can sign a ed25519 key with a RSA certificate)

Then, sign this key-pair with your Yubikey.
You may change the validity period using standard ssh-keygen stanzas, like ```d``` for days.

```ssh-keygen -D /usr/lib/x86_64-linux-gnu/libykcs11.so -s ca.pub -V "+12h" -I "username" -n user-id [key_to_sign]```
e.g.
```ssh-keygen -D /usr/lib/x86_64-linux-gnu/libykcs11.so -s ca.pub -V "+12h" -I 'myuser' -n myuserid user-key.pub```
which will generate a *-cert.pub, that is the signed certificate. This naming is standardized (implied by SSH), so keep it!

## Login to host accepting these keys

```SSH_AUTH_SOCK= ssh -i ./tmp-ansible-key  ansible@adpi0 -F /dev/null```

## Destroy

Destroy the private key you imported into the Yubikeys. WARNING: you will have to re-generate everything if you want to add another Yubikey.
