# My guide to setting up Yubikey using an airgapped system

The guide will assume you have (several) Yubikey 5s, and want to satisfy the following use-cases:

* Secure login through SSH
* PGP/GPG signing and encryption
* OTP source for online accounts

Then, here is the list of steps you will need to perform:

* [Prepare environment](#prepare-environment)
* [Install software](#install-software)
* [Prepare GnuPG](#prepare-gnupg)
  * [Configuration](#configuration)
  * [Identity](#identity)
  * [Key](#key)
  * [Expiration](#expiration)
  * [Passphrase](#passphrase)
* [Create Certify key](#create-certify-key)
* [Create Subkeys](#create-subkeys)
* [Verify keys](#verify-keys)
* [Backup keys](#backup-keys)
* [Export public key](#export-public-key)
* [Configure YubiKey](#configure-yubikey)
  * [Change PIN](#change-pin)
  * [Set attributes](#set-attributes)
* [Transfer Subkeys](#transfer-subkeys)
  * [Signature key](#signature-key)
  * [Encryption key](#encryption-key)
  * [Authentication key](#authentication-key)
* [Verify transfer](#verify-transfer)
* [Finish setup](#finish-setup)
* [Using YubiKey](#using-yubikey)
  * [Encryption](#encryption)
  * [Signature](#signature)
  * [Configure touch](#configure-touch)
  * [SSH](#ssh)
    * [Replace agents](#replace-agents)
    * [Copy public key](#copy-public-key)
    * [Import SSH keys](#import-ssh-keys)
    * [SSH agent forwarding](#ssh-agent-forwarding)
      * [Use ssh-agent](#use-ssh-agent)
      * [Use S.gpg-agent.ssh](#use-sgpg-agentssh)
      * [Chained forwarding](#chained-forwarding)
    * [GitHub](#github)
    * [GnuPG agent forwarding](#gnupg-agent-forwarding)
      * [Legacy distributions](#legacy-distributions)
      * [Chained GnuPG agent forwarding](#chained-gnupg-agent-forwarding)
    * [Using multiple YubiKeys](#using-multiple-yubikeys)
    * [Email](#email)
      * [Thunderbird](#thunderbird)
      * [Mailvelope](#mailvelope)
      * [Mutt](#mutt)
    * [Keyserver](#keyserver)
* [Updating keys](#updating-keys)
  * [Renew Subkeys](#renew-subkeys)
  * [Rotate Subkeys](#rotate-subkeys)
* [Reset YubiKey](#reset-yubikey)
* [Optional hardening](#optional-hardening)
  * [Improving entropy](#improving-entropy)
  * [Enable KDF](#enable-kdf)
  * [Network considerations](#network-considerations)
* [Notes](#notes)
* [Troubleshooting](#troubleshooting)
* [Alternative solutions](#alternative-solutions)
* [Additional resources](#additional-resources)

## Purchase YubiKey

[All YubiKeys](https://www.yubico.com/store/compare/) *except* FIDO-only Security Key Series and Bio Series YubiKeys are compatible with this guide.

[Verify YubiKey](https://support.yubico.com/hc/en-us/articles/360013723419-How-to-Confirm-Your-Yubico-Device-is-Genuine) by visiting [yubico.com/genuine](https://www.yubico.com/genuine/). Select *Verify Device* to begin the process. Touch the YubiKey when prompted and allow the site to see the make and model of the device when prompted. This device attestation may help mitigate [supply chain attacks](https://media.defcon.org/DEF%20CON%2025/DEF%20CON%2025%20presentations/DEF%20CON%2025%20-%20r00killah-and-securelyfitz-Secure-Tokin-and-Doobiekeys.pdf).

Several portable storage devices (such as microSD cards) for storing encrypted backups are also recommended.

## Prepare environment

A dedicated, secure operating environment is recommended to generate cryptographic keys.
Debian Bookworm is used in this guide to balance usability and security.

Power off, proceed to remove all unnecessary devices, such as the wireless card. Use the BIOS-settings to disable useless stuff.
I disabled the audio, bluetooth and wireless chips, for instance.

## Install software

The target for this guide will be an airgapped system. This means the system will never be connected to any network, except when installing/preparing the environment.

### Debian Bookworm

```console
sudo apt update

sudo apt -y upgrade

sudo apt -y install \
    wget gnupg2 gnupg-agent dirmngr \
    cryptsetup scdaemon pcscd \
    yubikey-personalization yubikey-manager \
    git
```

## Prepare GnuPG

Create or import a [hardened configuration](https://github.com/drduh/YubiKey-Guide/blob/master/config/gpg.conf):

```console
mkdir gnuconfig
cd gnuconfig
wget https://raw.githubusercontent.com/drduh/YubiKey-Guide/master/config/gpg.conf
```

Create a temporary directory which will be cleared on [reboot](https://en.wikipedia.org/wiki/Tmpfs) and set it as the GnuPG directory.
I suggest using the /run/user/$UID folder for this:

```console
export GNUPGHOME=$(mktemp -d -p /run/user/$UID -t $(date +%Y.%m.%d)-XXXX)
```

Then, place the configuration file you downloaded in this temporary directory:

```console
cp ~/gnuconfig/gpg.conf $GNUPGHOME/gpg.conf
```

Feel free to script this, as you will be doing this every time you use this airgapped system.
Run this script using the dot space notation, as you will be setting an environment variable, which will need to be
kept in the current shell (not solely in the context of the bash-script)

The script will look something like:

```console
#!/bin/bash

echo Script to prepare GNUPG
echo Run this with "dot space" in order to set environment variables

export GNUPGHOME=$(mktemp -d -p /run/user/$UID -t $(date +%Y.%m.%d)-XXXX)
cp ~/gnuconfig/gpg.conf $GNUPGHOME/gpg.conf
```

## Configuration within gpg.conf

The options will look similar to:

```console
$ grep -v "^#" $GNUPGHOME/gpg.conf
personal-cipher-preferences AES256 AES192 AES
personal-digest-preferences SHA512 SHA384 SHA256
personal-compress-preferences ZLIB BZIP2 ZIP Uncompressed
default-preference-list SHA512 SHA384 SHA256 AES256 AES192 AES ZLIB BZIP2 ZIP Uncompressed
cert-digest-algo SHA512
s2k-digest-algo SHA512
s2k-cipher-algo AES256
charset utf-8
no-comments
no-emit-version
no-greeting
keyid-format 0xlong
list-options show-uid-validity
verify-options show-uid-validity
with-fingerprint
require-cross-certification
require-secmem
no-symkey-cache
armor
use-agent
throw-keyids
```

> [!IMPORTANT]
> Networking should be disabled for the remainder of the setup.

## Identity

When creating an identity with GnuPG, the default options ask for a "Real name", "Email address" and optional "Comment".

Depending on how you plan to use GnuPG, set these values respectively[^1]:

```console
export IDENTITY="YubiKey User <yubikey@example.domain>"
```

Or use any attribute which will uniquely identity the key (this may be incompatible with certain use cases):

```console
export IDENTITY="My Cool YubiKey - 2025"
```

## Key

Set the algorithm and key size - RSA/4096 is recommended:

```console
export KEY_TYPE=rsa4096
```

## Expiration

Determine the desired Subkey validity duration.

Setting a Subkey expiry forces identity and credential lifecycle management. However, setting an expiry on the Certify key is pointless, because it can just be used to extend itself[^2].

This guide recommends a two year expiration for Subkeys to balance security and usability, however longer durations are possible to reduce maintenance frequency.

When Subkeys expire, they may still be used to decrypt with GnuPG and authenticate with SSH, however they can **not** be used to encrypt nor sign new messages.

Subkeys must be renewed or rotated using the Certify key - see [Updating keys](#updating-keys).

Set Subkeys to expire on a planned date:

```console
export EXPIRATION=2027-05-01
```

The expiration date may also be relative, for example set to two years from today:

```console
export EXPIRATION=2y
```

## Passphrase

Generate a passphrase for the Certify key. This credential will be used to manage identity Subkeys.

To improve readability, this guide recommends a passphrase consisting only of uppercase letters and numbers.

The following commands will generate a strong[^3] passphrase while avoiding certain similar-looking characters:

```console
export CERTIFY_PASS=$(LC_ALL=C tr -dc "A-Z2-9" < /dev/urandom | \
    tr -d "IOUS5" | \
    fold  -w  ${PASS_GROUPSIZE:-4} | \
    paste -sd ${PASS_DELIMITER:--} - | \
    head  -c  ${PASS_LENGTH:-29})
printf "\n$CERTIFY_PASS\n\n"
```

To change the passphrase length, delimiting character or group sizes, export the respective variable(s) prior to running the passphrase generation command, for example:

```console
export PASS_GROUPSIZE=6
export PASS_DELIMITER=+
export PASS_LENGTH=48
```

Write the passphrase in a secure location - separate from the portable storage device used for key material, or memorize it.

This repository includes a [`passphrase.html`](https://raw.githubusercontent.com/drduh/YubiKey-Guide/master/templates/passphrase.html) template to help with credential transcription. Save the [raw file](https://github.com/drduh/YubiKey-Guide/raw/refs/heads/master/templates/passphrase.html), open in a browser to render and print.

Mark the corresponding character on sequential rows for each character in the passphrase. [`passphrase.txt`](https://raw.githubusercontent.com/drduh/YubiKey-Guide/master/templates/passphrase.txt) can also be printed without a browser:

```console
lp -d Printer-Name passphrase.txt
```

[Diceware](https://secure.research.vt.edu/diceware) is another popular method for creating memorable passphrases.

## Create Certify key

The primary key to generate is the Certify key, which is responsible for issuing Subkeys for encryption, signature and authentication operations.

The Certify key should be kept offline at all times and only accessed from a dedicated and secure environment to issue or revoke Subkeys.

Do not set an expiration date on the Certify key.

Generate the Certify key:

```console
echo "$CERTIFY_PASS" | \
    gpg --batch --passphrase-fd 0 \
        --quick-generate-key "$IDENTITY" "$KEY_TYPE" cert never
```

Set and view the Certify key identifier and fingerprint for use later:

```console
export KEYID=$(gpg -k --with-colons "$IDENTITY" | \
    awk -F: '/^pub:/ { print $5; exit }')

export KEYFP=$(gpg -k --with-colons "$IDENTITY" | \
    awk -F: '/^fpr:/ { print $10; exit }')

printf "\nKey ID: %40s\nKey FP: %40s\n\n" "$KEYID" "$KEYFP"
```

### Add additional IDs (optional)

This is an optional step for use cases requiring additional identities:

Define an array containing additional user IDs. Each array element must be wrapped in quotes and each element must be space-delimited:

```console
declare -a additional_uids
additional_uids=("Super Cool YubiKey 2025" "uid 1 <uid1@example.org>")
```

Add the additional user IDs to the Certify key:

```console
for uid in "${additional_uids[@]}" ; do \
    echo "$CERTIFY_PASS" | \
    gpg --batch --passphrase-fd 0 \
        --pinentry-mode=loopback --quick-add-uid "$KEYFP" "$uid"
done
```

Adjust the trust of the additional IDs to *ultimate*:

```console
gpg --command-fd=0 --pinentry-mode=loopback --edit-key "$KEYID" <<EOF
uid *
trust
5
y
save
EOF
```
</details>

# Create Subkeys

Generate Signature, Encryption and Authentication Subkeys using the previously configured key type, passphrase and expiration:

```console
for SUBKEY in sign encrypt auth ; do \
    echo "$CERTIFY_PASS" | \
    gpg --batch --pinentry-mode=loopback --passphrase-fd 0 \
        --quick-add-key "$KEYFP" "$KEY_TYPE" "$SUBKEY" "$EXPIRATION"
done
```

# Verify keys

List available secret keys:

```console
gpg -K
```

The output will display **[C]ertify, [S]ignature, [E]ncryption and [A]uthentication** keys:

```console
sec   rsa4096/0xF0F2CFEB04341FB5 2025-01-01 [C]
      Key fingerprint = 4E2C 1FA3 372C BA96 A06A  C34A F0F2 CFEB 0434 1FB5
uid                   [ultimate] YubiKey User <yubikey@example>
ssb   rsa4096/0xB3CD10E502E19637 2025-01-01 [S] [expires: 2027-05-01]
ssb   rsa4096/0x30CBE8C4B085B9F7 2025-01-01 [E] [expires: 2027-05-01]
ssb   rsa4096/0xAD9E24E1B8CB9600 2025-01-01 [A] [expires: 2027-05-01]
```

# Backup keys

Save a copy of the Certify key, Subkeys and public key:

```console
echo "$CERTIFY_PASS" | \
    gpg --output $GNUPGHOME/$KEYID-Certify.key \
        --batch --pinentry-mode=loopback --passphrase-fd 0 \
        --armor --export-secret-keys $KEYID

echo "$CERTIFY_PASS" | \
    gpg --output $GNUPGHOME/$KEYID-Subkeys.key \
        --batch --pinentry-mode=loopback --passphrase-fd 0 \
        --armor --export-secret-subkeys $KEYID

gpg --output $GNUPGHOME/$KEYID-$(date +%F).asc \
    --armor --export $KEYID
```

# Export public key

> [!IMPORTANT]
> Without the public key, it will **not** be possible to use GnuPG to decrypt/sign messages. However, YubiKey can still be used for SSH authentication.

```console

gpg --armor --export $KEYID | sudo tee $KEYID-$(date +%F).asc
sudo chmod 0444 *.asc
```

## Configure YubiKey

Connect YubiKey and confirm its status:

```console
gpg --card-status
```

If the YubiKey is locked, [Reset](#reset-yubikey) it.

## Change PIN

YubiKey's [PGP](https://developers.yubico.com/PGP/) interface has its own PINs separate from other modules such as [PIV](https://developers.yubico.com/PIV/Introduction/YubiKey_and_PIV.html):

Name | Default | Capability
:---: | :---: | ---
User PIN | `123456` | cryptographic operations (decrypt, sign, authenticate)
Admin PIN | `12345678` | reset PIN, change Reset Code, add keys and owner information
Reset Code | None | reset PIN ([more information](https://forum.yubico.com/viewtopicd01c.html?p=9055#p9055))

Determine the desired PIN values. They can be shorter than the Certify key passphrase due to limited brute-forcing opportunities; the User PIN should be convenient enough to remember for every-day use.

The *User PIN* must be at least 6 characters and the *Admin PIN* must be at least 8 characters. A maximum of 127 ASCII characters are allowed. See [Managing PINs](https://www.gnupg.org/howtos/card-howto/en/ch03s02.html) for more information.

Set PIN values, for example a 6 digit User PIN and 8 digit Admin PIN:

```console
export ADMIN_PIN=$(LC_ALL=C tr -dc '0-9' < /dev/urandom | \
    fold -w8 | head -1)

export USER_PIN=$(LC_ALL=C tr -dc '0-9' < /dev/urandom | \
    fold -w6 | head -1)

printf "\nAdmin PIN: %12s\nUser PIN: %13s\n\n" \
    "$ADMIN_PIN" "$USER_PIN"
```

Change the Admin PIN:

```console
gpg --command-fd=0 --pinentry-mode=loopback --change-pin <<EOF
3
12345678
$ADMIN_PIN
$ADMIN_PIN
q
EOF
```

Change the User PIN:

```console
gpg --command-fd=0 --pinentry-mode=loopback --change-pin <<EOF
1
123456
$USER_PIN
$USER_PIN
q
EOF
```

Remove and re-insert YubiKey.

> [!CAUTION]
> Three incorrect *User PIN* entries will cause it to become blocked and must be unblocked with either the *Admin PIN* or *Reset Code*. Three incorrect *Admin PIN* or *Reset Code* entries will destroy data on YubiKey.

The number of [retry attempts](https://docs.yubico.com/software/yubikey/tools/ykman/OpenPGP_Commands.html#ykman-openpgp-access-set-retries-options-pin-retries-reset-code-retries-admin-pin-retries) can be changed, for example to 5 attempts:

```console
ykman openpgp access set-retries 5 5 5 -f -a $ADMIN_PIN
```

## Set attributes

Use previously set values:

```console
gpg --command-fd=0 --pinentry-mode=loopback --edit-card <<EOF
admin
login
$IDENTITY
$ADMIN_PIN
quit
EOF
```

[Smart card attributes](https://gnupg.org/howtos/card-howto/en/smartcard-howto-single.html) can also be set with `gpg --edit-card` and `admin` mode. Use `help` to see available options. The `login` attribute is [required](https://github.com/drduh/YubiKey-Guide/issues/461).

Run `gpg --card-status` to verify results (*Login data* field).

# Transfer Subkeys

> [!IMPORTANT]
> Transferring keys to YubiKey converts the on-disk key into a "stub" - making it no longer usable to transfer to subsequent YubiKeys. Ensure keys were backed up before proceeding.

The Certify key passphrase and Admin PIN are required to transfer keys.

## Signature key

Transfer the Signature key:

```console
gpg --command-fd=0 --pinentry-mode=loopback --edit-key $KEYID <<EOF
key 1
keytocard
1
$CERTIFY_PASS
$ADMIN_PIN
save
EOF
```

## Encryption key

Repeat the process for the Encryption key:

```console
gpg --command-fd=0 --pinentry-mode=loopback --edit-key $KEYID <<EOF
key 2
keytocard
2
$CERTIFY_PASS
$ADMIN_PIN
save
EOF
```

## Authentication key

Repeat the process for the Authentication key:

```console
gpg --command-fd=0 --pinentry-mode=loopback --edit-key $KEYID <<EOF
key 3
keytocard
3
$CERTIFY_PASS
$ADMIN_PIN
save
EOF
```

# Verify transfer

Verify Subkeys are on YubiKey with `gpg -K` - indicated by `ssb>`:

```console
sec   rsa4096/0xF0F2CFEB04341FB5 2025-01-01 [C]
      Key fingerprint = 4E2C 1FA3 372C BA96 A06A  C34A F0F2 CFEB 0434 1FB5
uid                   [ultimate] YubiKey User <yubikey@example>
ssb>  rsa4096/0xB3CD10E502E19637 2025-01-01 [S] [expires: 2027-05-01]
ssb>  rsa4096/0x30CBE8C4B085B9F7 2025-01-01 [E] [expires: 2027-05-01]
ssb>  rsa4096/0xAD9E24E1B8CB9600 2025-01-01 [A] [expires: 2027-05-01]
```

The `>` after a tag indicates the key is stored on a smart card.

# Finish setup

Verify the following steps were performed correctly:

- [ ] Memorized or wrote down the Certify key (identity) passphrase to a secure and durable location
  * `echo $CERTIFY_PASS` to see it again; [`passphrase.html`](https://raw.githubusercontent.com/drduh/YubiKey-Guide/master/templates/passphrase.html) or [`passphrase.txt`](https://raw.githubusercontent.com/drduh/YubiKey-Guide/master/templates/passphrase.txt) to transcribe it
- [ ] Memorized or wrote down passphrase to encrypted volume on portable storage
  * `echo $LUKS_PASS` to see it again; [`passphrase.html`](https://raw.githubusercontent.com/drduh/YubiKey-Guide/master/templates/passphrase.html) or [`passphrase.txt`](https://raw.githubusercontent.com/drduh/YubiKey-Guide/master/templates/passphrase.txt) to transcribe it
- [ ] Saved the Certify key and Subkeys to encrypted portable storage, to be kept offline
  * At least two backups are recommended, stored at separate locations
- [ ] Exported a copy of the public key where is can be easily accessed later
  * Separate device or non-encrypted partition was used
- [ ] Memorized or wrote down the User PIN and Admin PIN, which are unique and changed from default values
  * `echo $USER_PIN $ADMIN_PIN` to see them again; [`passphrase.html`](https://raw.githubusercontent.com/drduh/YubiKey-Guide/master/templates/passphrase.html) or [`passphrase.txt`](https://raw.githubusercontent.com/drduh/YubiKey-Guide/master/templates/passphrase.txt) to transcribe them
- [ ] Moved Encryption, Signature and Authentication Subkeys to YubiKey
  * `gpg -K` shows `ssb>` for each of the 3 Subkeys

Reboot, clearing the ephemeral environment, to complete setup.

# Using YubiKey

Initialize GnuPG:

```console
gpg -k
```

Create or import a [hardened configuration](https://github.com/drduh/YubiKey-Guide/blob/master/config/gpg.conf):

```console
cd ~/.gnupg

wget https://raw.githubusercontent.com/drduh/YubiKey-Guide/master/config/gpg.conf
```

Set the following option. This avoids the problem where GnuPG will repeatedly prompt for the insertion of an already-inserted YubiKey:

```console
touch scdaemon.conf

echo "disable-ccid" >>scdaemon.conf
```

Install the required packages:

**Debian/Ubuntu**

```console
sudo apt update

sudo apt install -y gnupg gnupg-agent scdaemon pcscd
```

**Arch**

```console
sudo pacman -S --needed gnupg pcsc-tools

sudo systemctl enable --now pcscd.service
```

**macOS**

```console
sudo port install gnupg2 pcsc-tools
```

**OpenBSD**

```console
doas pkg_add gnupg pcsc-tools

doas rcctl enable pcscd

doas reboot
```

Mount the non-encrypted volume with the public key:

**Debian/Ubuntu**

```console
sudo mkdir /mnt/public

sudo mount /dev/sdc2 /mnt/public
```

**OpenBSD**

```console
doas mkdir /mnt/public

doas mount /dev/sd3i /mnt/public
```

Import the public key:

```console
gpg --import /mnt/public/*.asc
```

Or download the public key from a keyserver:

```console
gpg --recv $KEYID
```

Or with the URL on YubiKey, retrieve the public key:

using the command `gpg-card`

```console
gpg/card> fetch

gpg/card> quit
```

Determine the key ID:

```console
gpg -k

export KEYID=0xF0F2CFEB04341FB5
```

Assign ultimate trust by typing `trust` and selecting option `5` then `quit`:

```console
gpg --command-fd=0 --pinentry-mode=loopback --edit-key $KEYID <<EOF
trust
5
y
save
EOF
```

Remove and re-insert YubiKey.

Verify the status with `gpg --card-status` which will list the available Subkeys:

```console
Reader ...........: Yubico YubiKey OTP FIDO CCID 00 00
Application ID ...: D2760001240102010006055532110000
Application type .: OpenPGP
Version ..........: 3.4
Manufacturer .....: Yubico
Serial number ....: 05553211
Name of cardholder: YubiKey User
Language prefs ...: en
Salutation .......:
URL of public key : [not set]
Login data .......: yubikey@example
Signature PIN ....: not forced
Key attributes ...: rsa4096 rsa4096 rsa4096
Max. PIN lengths .: 127 127 127
PIN retry counter : 3 3 3
Signature counter : 0
KDF setting ......: on
Signature key ....: CF5A 305B 808B 7A0F 230D  A064 B3CD 10E5 02E1 9637
      created ....: 2025-01-01 12:00:00
Encryption key....: A5FA A005 5BED 4DC9 889D  38BC 30CB E8C4 B085 B9F7
      created ....: 2025-01-01 12:00:00
Authentication key: 570E 1355 6D01 4C04 8B6D  E2A3 AD9E 24E1 B8CB 9600
      created ....: 2025-01-01 12:00:00
General key info..: sub  rsa4096/0xB3CD10E502E19637 2025-01-01 YubiKey User <yubikey@example>
sec#  rsa4096/0xF0F2CFEB04341FB5  created: 2025-01-01  expires: never
ssb>  rsa4096/0xB3CD10E502E19637  created: 2025-01-01  expires: 2027-05-01
                                  card-no: 0006 05553211
ssb>  rsa4096/0x30CBE8C4B085B9F7  created: 2025-01-01  expires: 2027-05-01
                                  card-no: 0006 05553211
ssb>  rsa4096/0xAD9E24E1B8CB9600  created: 2025-01-01  expires: 2027-05-01
                                  card-no: 0006 05553211
```

`sec#` indicates the corresponding key is not available (the Certify key is offline).

YubiKey is now ready for use!

## Encryption

Encrypt a message to yourself (useful for storing credentials or protecting backups):

```console
echo -e "\ntest message string" | \
    gpg --encrypt --armor \
        --recipient $KEYID --output encrypted.txt
```

Decrypt the message - a prompt for the User PIN will appear:

```console
gpg --decrypt --armor encrypted.txt
```

To encrypt to multiple recipients/keys, set the preferred key ID last:

```console
echo "test message string" | \
    gpg --encrypt --armor \
        --recipient $KEYID_2 --recipient $KEYID_1 --recipient $KEYID \
        --output encrypted.txt
```

Use a [shell function](https://github.com/drduh/config/blob/main/zshrc) to make encrypting files easier:

```console
secret () {
  output="${1}".$(date +%s).enc
  gpg --encrypt --armor --output ${output} \
    -r $KEYID "${1}" && echo "${1} -> ${output}"
}

reveal () {
  output=$(echo "${1}" | rev | cut -c16- | rev)
  gpg --decrypt --output ${output} "${1}" && \
    echo "${1} -> ${output}"
}
```

Example output:

```console
$ secret document.pdf
document.pdf -> document.pdf.1580000000.enc

$ reveal document.pdf.1580000000.enc
gpg: anonymous recipient; trying secret key 0xF0F2CFEB04341FB5 ...
gpg: okay, we are the anonymous recipient.
gpg: encrypted with RSA key, ID 0x0000000000000000
document.pdf.1580000000.enc -> document.pdf
```

[drduh/Purse](https://github.com/drduh/Purse) is a password manager based on GnuPG and YubiKey to securely store and use credentials.

## Signature

Sign a message:

```console
echo "test message string" | gpg --armor --clearsign > signed.txt
```

Verify the signature:

```console
gpg --verify signed.txt
```

The output will be similar to:

```console
gpg: Signature made Mon 01 Jan 2025 12:00:00 PM UTC
gpg:                using RSA key CF5A305B808B7A0F230DA064B3CD10E502E19637
gpg: Good signature from "YubiKey User <yubikey@example>" [ultimate]
Primary key fingerprint: 4E2C 1FA3 372C BA96 A06A  C34A F0F2 CFEB 0434 1FB5
     Subkey fingerprint: CF5A 305B 808B 7A0F 230D  A064 B3CD 10E5 02E1 9637
```

## Configure touch

By default, YubiKey will perform cryptographic operations without requiring any action from the user after the key is unlocked once with the PIN.

To require a touch for each key operation, use [YubiKey Manager](https://developers.yubico.com/yubikey-manager/) and the Admin PIN to set key policy.

Encryption:

```console
ykman openpgp keys set-touch dec on
```

> [!NOTE]
> YubiKey Manager prior to versions 5.1.0 use `enc` instead of `dec` for encryption:

```console
ykman openpgp keys set-touch enc on
```

Even older versions of YubiKey Manager use `touch` instead of `set-touch`

Signature:

```console
ykman openpgp keys set-touch sig on
```

Authentication:

```console
ykman openpgp keys set-touch aut on
```

To view and adjust policy options:

```console
ykman openpgp keys set-touch -h
```

`Cached` or `Cached-Fixed` may be desirable for YubiKey use with email clients.

YubiKey will blink when it is waiting for a touch. On Linux, [maximbaz/yubikey-touch-detector](https://github.com/maximbaz/yubikey-touch-detector) can be used to indicate YubiKey is waiting for a touch.

## SSH

Create or import a [hardened configuration](https://github.com/drduh/YubiKey-Guide/blob/master/config/gpg-agent.conf):

```console
cd ~/.gnupg

wget https://raw.githubusercontent.com/drduh/YubiKey-Guide/master/config/gpg-agent.conf
```

> [!NOTE]
> `cache-ttl` options do **not** apply when using YubiKey as a smart card, because the PIN is [cached by the smart card itself](https://dev.gnupg.org/T3362). To clear the PIN from cache (equivalent to `default-cache-ttl` and `max-cache-ttl`), remove YubiKey, or set `forcesig` when editing the card to be prompted for the PIN each time.

> [!TIP]
> Set `pinentry-program` to `/usr/bin/pinentry-gnome3` for a GUI-based prompt.

**macOS**

Install pinentry with `brew install pinentry-mac` or `sudo port install pinentry` then edit `gpg-agent.conf` to set the `pinentry-program` path to:

* Apple Silicon Macs: `/opt/homebrew/bin/pinentry-mac`
* Intel Macs: `/usr/local/bin/pinentry-mac` or `/opt/local/bin/pinentry` (MacPorts)
* MacGPG Suite: `/usr/local/MacGPG2/libexec/pinentry-mac.app/Contents/MacOS/pinentry-mac`

Then run `gpgconf --kill gpg-agent` for the change to take effect.

To use graphical applications on macOS, [additional setup is required](https://jms1.net/yubikey/make-ssh-use-gpg-agent.md).

Create `$HOME/Library/LaunchAgents/gnupg.gpg-agent.plist` with the following contents:

```
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
    <dict>
        <key>Label</key>
        <string>gnupg.gpg-agent</string>
        <key>RunAtLoad</key>
        <true/>
        <key>KeepAlive</key>
        <false/>
        <key>ProgramArguments</key>
        <array>
            <string>/usr/local/MacGPG2/bin/gpg-connect-agent</string>
            <string>/bye</string>
        </array>
    </dict>
</plist>
```

Load it:

```console
launchctl load $HOME/Library/LaunchAgents/gnupg.gpg-agent.plist
```

Create `$HOME/Library/LaunchAgents/gnupg.gpg-agent-symlink.plist` with the following contens:

```
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/ProperyList-1.0/dtd">
<plist version="1.0">
    <dict>
        <key>Label</key>
        <string>gnupg.gpg-agent-symlink</string>
        <key>ProgramArguments</key>
        <array>
            <string>/bin/sh</string>
            <string>-c</string>
            <string>/bin/ln -sf $HOME/.gnupg/S.gpg-agent.ssh $SSH_AUTH_SOCK</string>
        </array>
        <key>RunAtLoad</key>
        <true/>
    </dict>
</plist>
```

Load it:

```console
launchctl load $HOME/Library/LaunchAgents/gnupg.gpg-agent-symlink.plist
```

Reboot to activate changes.

**Windows**

Windows can already have some virtual smart card readers installed, like the one provided for Windows Hello. To verify YubiKey is the correct one used by scdaemon, add it to its configuration.

Find the YubiKey label using PowerShell:

```powershell
PS C:\WINDOWS\system32> Get-PnpDevice -Class SoftwareDevice | Where-Object {$_.FriendlyName -like "*YubiKey*"} | Select-Object -ExpandProperty FriendlyName
Yubico YubiKey OTP+FIDO+CCID 0
```

See [How to setup Signed Git Commits with a YubiKey NEO and GPG and Keybase on Windows (2018)](https://www.hanselman.com/blog/HowToSetupSignedGitCommitsWithAYubiKeyNEOAndGPGAndKeybaseOnWindows.aspx) for more information.

Edit `%APPDATA%/gnupg/scdaemon.conf` to add:

```console
reader-port <device name, e.g. Yubico YubiKey OTP+FIDO+CCID 0>
```

Edit `%APPDATA%/gnupg/gpg-agent.conf` to add:

```console
enable-ssh-support
enable-putty-support
```

Restart the agent:

```console
gpg-connect-agent killagent /bye

gpg-connect-agent /bye
```

Verify YubiKey details:

```console
gpg --card-status
```

Import the public key and set ultimate trust:

```console
gpg --import <path to public key file>
```

Retrieve the public key id:

```console
gpg --list-public-keys
```

Export the SSH public key:

```console
gpg --export-ssh-key <public key id>
```

Copy the public SSH key to a file - it corresponds to the secret key on YubiKey and can be copied to SSH destination hosts.

Create a shortcut that points to `gpg-connect-agent /bye` and place it in the startup folder `shell:startup` to make sure the agent starts after reboot. Modify the shortcut properties so it starts in a "Minimized" window.

PuTTY can now be used for public-key SSH authentication. When the server asks for public-key verification, PuTTY will forward the request to GnuPG, which will prompt for a PIN to authorize the operation.

**WSL**

The goal is to configure SSH client inside WSL work together with the Windows agent, such as gpg-agent.exe.

See the [WSL agent architecture](media/schema_gpg.png) illustration for an overview.

GnuPG forwarding for cryptographic operations is not supported. See [vuori/weasel-pageant](https://github.com/vuori/weasel-pageant) for more information.

One way to forward is just `ssh -A` (still need to eval weasel to setup local ssh-agent), and only relies on OpenSSH. In this track, `ForwardAgent` and `AllowAgentForwarding` in ssh/sshd config may be involved. However, when using ssh socket forwarding, do not enable `ForwardAgent` in ssh config. See [SSH Agent Forwarding](#ssh-agent-forwarding) for more information. This requires Ubuntu 16.04 or newer for WSL and Kleopatra.

Download [vuori/weasel-pageant](https://github.com/vuori/weasel-pageant).

Add `eval $(/mnt/c/<path of extraction>/weasel-pageant -r -a /tmp/S.weasel-pageant)` to the shell rc file. Use a named socket here so it can be used in the `RemoteForward` directive of `~/.ssh/config`. Source it with `source ~/.bashrc`.

Display the SSH key with `$ ssh-add -l`

Edit `~/.ssh/config` to add the following for each agent forwarding host:

```console
RemoteForward <remote SSH socket path> /tmp/S.weasel-pageant
```

The remote SSH socket path can be found with `gpgconf --list-dirs agent-ssh-socket`

Add the following to the shell rc file:

```console
export SSH_AUTH_SOCK=$(gpgconf --list-dirs agent-ssh-socket)
```

Add the following to `/etc/ssh/sshd_config`:

```console
StreamLocalBindUnlink yes
```

Reload SSH daemon:

```console
sudo service sshd reload
```

Remove YubiKey and reboot. Log back into Windows, open a WSL console and enter `ssh-add -l` - no output should appear.

Plug in YubiKey, enter the same command to display the ssh key.

Connect to the remote host and use `ssh-add -l` to confirm forwarding works.

Agent forwarding may be chained through multiple hosts. Follow the same [protocol](#remote-host-configuration) to configure each host.

An alternate method is the [usbipd-win](https://github.com/dorssel/usbipd-win) library. If you encounter issues with accessing the YubiKey in WSL after configuring usbipd-win, you may need to add custom polkit rules to ensure proper permissions for the pcscd service. Here's an example configuration using a scard group (the group logic is optional):

Create a new rule file at /etc/polkit-1/rules.d/99-pcscd.rules:

```bash
polkit.addRule(function(action, subject) {
    if (action.id == "org.debian.pcsc-lite.access_card" &&
        subject.isInGroup("scard")) {
        return polkit.Result.YES;
    }
});

polkit.addRule(function(action, subject) {
    if (action.id == "org.debian.pcsc-lite.access_pcsc" &&
        subject.isInGroup("scard")) {
        return polkit.Result.YES;
    }
});
```

### Replace agents

To launch `gpg-agent` for use by SSH, use the `gpg-connect-agent /bye` or `gpgconf --launch gpg-agent` commands.

Add the following to the shell rc file:

```console
export GPG_TTY=$(tty)
export SSH_AUTH_SOCK=$(gpgconf --list-dirs agent-ssh-socket)
gpgconf --launch gpg-agent
gpg-connect-agent updatestartuptty /bye > /dev/null
```

For fish, `config.fish` should look like this (consider putting them into the `is-interactive` block):

```fish
set -x GPG_TTY (tty)
set -x SSH_AUTH_SOCK (gpgconf --list-dirs agent-ssh-socket)
gpgconf --launch gpg-agent
```

When using `ForwardAgent` for ssh-agent forwarding, `SSH_AUTH_SOCK` only needs to be set on the *local* host, where YubiKey is connected. On the *remote* host, `ssh` will set `SSH_AUTH_SOCK` to something like `/tmp/ssh-mXzCzYT2Np/agent.7541` upon connection. Do **not** set `SSH_AUTH_SOCK` on the remote host - doing so will break [SSH Agent Forwarding](#ssh-agent-forwarding).

For `S.gpg-agent.ssh` (see [SSH Agent Forwarding](#ssh-agent-forwarding) for more info), `SSH_AUTH_SOCK` should also be set on the *remote*. However, `GPG_TTY` should not be set on the *remote*, explanation specified in that section.

### Copy public key

> [!TIP]
> It is **not** necessary to import the GnuPG public key in order to use SSH only.

Copy and paste the output from `ssh-add` to the server's `authorized_keys` file:

```console
$ ssh-add -L
ssh-rsa AAAAB4NzaC1yc2EAAAADAQABAAACAz[...]zreOKM+HwpkHzcy9DQcVG2Nw== cardno:000605553211
```

**Optional** Save the public key for identity file configuration. By default, SSH attempts to use all the identities available via the agent. It's often a good idea to manage exactly which keys SSH will use to connect to a server, for example to separate different roles or [to avoid being fingerprinted by untrusted ssh servers](https://words.filippo.io/ssh-whoami-filippo-io/). To do this you'll need to use the command line argument `-i [identity_file]` or the `IdentityFile` and `IdentitiesOnly` options in `.ssh/config`.

The argument provided to `IdentityFile` is traditionally the path to the _private_ key file (for example `IdentityFile ~/.ssh/id_rsa`). For YubiKey, `IdentityFile` must point to the _public_ key file, and `ssh` will select the appropriate private key from those available via ssh-agent. To prevent `ssh` from trying all keys in the agent, use `IdentitiesOnly yes` along with one or more `-i` or `IdentityFile` options for the target host.

To reiterate, with `IdentitiesOnly yes`, `ssh` will not enumerate public keys loaded into `ssh-agent` or `gpg-agent`. This means public-key authentication will not proceed unless explicitly named by `ssh -i [identity_file]` or in `.ssh/config` on a per-host basis.

In the case of YubiKey usage, to extract the public key from the ssh agent:

```console
ssh-add -L | grep "cardno:000605553211" > ~/.ssh/id_rsa_yubikey.pub
```

Then explicitly associate this YubiKey-stored key for used with a host, `github.com` for example, as follows:

```console
$ cat << EOF >> ~/.ssh/config
Host github.com
    IdentitiesOnly yes
    IdentityFile ~/.ssh/id_rsa_yubikey.pub
EOF
```

Connect with public key authentication:

```console
$ ssh git@github.com -vvv
[...]
debug2: key: cardno:000605553211 (0x1234567890),
debug1: Authentications that can continue: publickey
debug3: start over, passed a different list publickey
debug3: preferred gssapi-keyex,gssapi-with-mic,publickey,keyboard-interactive,password
debug3: authmethod_lookup publickey
debug3: remaining preferred: keyboard-interactive,password
debug3: authmethod_is_enabled publickey
debug1: Next authentication method: publickey
debug1: Offering RSA public key: cardno:000605553211
debug3: send_pubkey_test
debug2: we sent a publickey packet, wait for reply
debug1: Server accepts key: pkalg ssh-rsa blen 535
debug2: input_userauth_pk_ok: fp e5:de:a5:74:b1:3e:96:9b:85:46:e7:28:53:b4:82:c3
debug3: sign_and_send_pubkey: RSA e5:de:a5:74:b1:3e:96:9b:85:46:e7:28:53:b4:82:c3
debug1: Authentication succeeded (publickey).
[...]
```

> [!TIP]
> To enable multiple connections, use the [ControlMaster](https://en.wikibooks.org/wiki/OpenSSH/Cookbook/Multiplexing) SSH option.

### Import SSH keys

If there are existing SSH keys to make available via `gpg-agent`, they will need to be imported. Then, remove the original private keys. When importing the key, `gpg-agent` uses the key filename as the label - this makes it easier to follow where the key originated from. In this example, we're starting with just the YubiKey in place and importing `~/.ssh/id_rsa`:

```console
$ ssh-add -l
4096 SHA256:... cardno:00060123456 (RSA)

$ ssh-add ~/.ssh/id_rsa && rm ~/.ssh/id_rsa
```

When invoking `ssh-add`, a prompt for the SSH key passphrase will appear, then the `pinentry` program will prompt and confirm a new passphrase to encrypt the converted key within the GnuPG key store.

The migrated key will be listed in `ssh-add -l`:

```console
$ ssh-add -l
4096 SHA256:... cardno:00060123456 (RSA)
2048 SHA256:... /Users/username/.ssh/id_rsa (RSA)
```

To show the keys with MD5 fingerprints, as used by `gpg-connect-agent`'s `KEYINFO` and `DELETE_KEY` commands:

```console
$ ssh-add -E md5 -l
4096 MD5:... cardno:00060123456 (RSA)
2048 MD5:... /Users/username/.ssh/id_rsa (RSA)
```

When using the key `pinentry` will be invoked to request the key passphrase. The passphrase will be cached for up to 10 idle minutes between uses, up to a maximum of 2 hours.

### SSH agent forwarding

> [!CAUTION]
> SSH Agent Forwarding can [add additional risk](https://matrix.org/blog/2019/05/08/post-mortem-and-remediations-for-apr-11-security-incident/#ssh-agent-forwarding-should-be-disabled) - proceed with caution!

There are two methods for ssh-agent forwarding, one is provided by OpenSSH and the other is provided by GnuPG.

The latter one may be more insecure as raw socket is just forwarded (not like `S.gpg-agent.extra` with only limited functionality; if `ForwardAgent` implemented by OpenSSH is just forwarding the raw socket, then they are insecure to the same degree). But for the latter one, one convenience is that one may forward once and use this agent everywhere in the remote. So again, proceed with caution!

For example, tmux does not have environment variables such as `$SSH_AUTH_SOCK` when connecting to remote hosts and attaching an existing session. For each shell, find the socket and `export SSH_AUTH_SOCK=/tmp/ssh-agent-xxx/xxxx.socket`. However, with `S.gpg-agent.ssh` in a fixed place, it can be used as the ssh-agent in shell rc files.

#### Use ssh-agent

You should now be able to use `ssh -A remote` on the _local_ host to log into _remote_ host, and should then be able to use YubiKey as if it were connected to the remote host. For example, using e.g. `ssh-add -l` on that remote host will show the public key from the YubiKey (`cardno:`). Always use `ForwardAgent yes` only for a single host, never for all servers.

#### Use S.gpg-agent.ssh

First you need to go through [GnuPG agent forwarding)](#gnupg-agent-forwarding), know the conditions for gpg-agent forwarding and know the location of `S.gpg-agent.ssh` on both the local and the remote.

You may use the command:

```console
$ gpgconf --list-dirs agent-ssh-socket
```

Edit `.ssh/config` to add the remote host:

```console
Host
    Hostname remote-host.tld
    StreamLocalBindUnlink yes
    RemoteForward /run/user/1000/gnupg/S.gpg-agent.ssh /run/user/1000/gnupg/S.gpg-agent.ssh
    #RemoteForward [remote socket] [local socket]
    #Note that ForwardAgent is not wanted here!
```

After successfully ssh into the remote host, confirm `/run/user/1000/gnupg/S.gpg-agent.ssh` exists.

Then in the *remote* you can type in command line or configure in the shell rc file with:

```console
export SSH_AUTH_SOCK="/run/user/$UID/gnupg/S.gpg-agent.ssh"
```

After sourcing the shell rc file, `ssh-add -l` will return the correct public key.

In this process no gpg-agent in the remote is involved, hence `gpg-agent.conf` in the remote is of no use. Also pinentry is invoked locally.

#### Chained forwarding

If you use `ssh-agent` provided by OpenSSH and want to forward it into a *third* box, you can just `ssh -A third` on the *remote*.

Meanwhile, if you use `S.gpg-agent.ssh`, assume you have gone through the steps above and have `S.gpg-agent.ssh` on the *remote*, and you would like to forward this agent into a *third* box, first you may need to configure `sshd_config` and `SSH_AUTH_SOCK` of *third* in the same way as *remote*, then in the ssh config of *remote*, add the following lines

```console
Host third
    Hostname third-host.tld
    StreamLocalBindUnlink yes
    RemoteForward /run/user/1000/gnupg/S.gpg-agent.ssh /run/user/1000/gnupg/S.gpg-agent.ssh
    #RemoteForward [remote socket] [local socket]
    #Note that ForwardAgent is not wanted here!
```

The path must be set according to `gpgconf --list-dirs agent-ssh-socket` on *remote* and *third* hosts.

## GitHub

YubiKey can be used to sign commits and tags, and authenticate SSH to GitHub when configured in [Settings](https://github.com/settings/keys).

Configure the signing key:

```console
git config --global user.signingkey $KEYID
```

Alternatively, if you are using the aforementioned `IdentityFile` (SSH key) for signing:

```console
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_rsa_yubikey.pub
```

Configure the `user.name` and `user.email` option to match the email address associated with the PGP identity:

```console
git config --global user.name 'YubiKey User'
git config --global user.email yubikey@example
```

To sign commits or tags, use the `-S` option, or consider enabling commit and tag signing by default:

```console
git config --global commit.gpgsign true
git config --global tag.gpgSign true
```

**Windows**

Configure authentication:

```console
git config --global core.sshcommand "plink -agent"

git config --global gpg.program 'C:\Program Files (x86)\GnuPG\bin\gpg.exe'
```

Then update the repository URL to `git@github.com:USERNAME/repository`

## GnuPG agent forwarding

YubiKey can be used sign git commits and decrypt files on remote hosts with GnuPG Agent Forwarding. To ssh through another network, especially to push to/pull from GitHub using ssh, see [Remote Machines (SSH Agent forwarding)](#ssh-agent-forwarding).

`gpg-agent.conf` is not needed on the remote host; after forwarding, remote GnuPG directly communicates with `S.gpg-agent` without starting `gpg-agent` on the remote host.

On the remote host, edit `/etc/ssh/sshd_config` to set `StreamLocalBindUnlink yes`

**Optional** Without root access on the remote host to edit `/etc/ssh/sshd_config`, socket located at `gpgconf --list-dir agent-socket` on the remote host will need to be removed before forwarding works. See [AgentForwarding GNUPG wiki page](https://wiki.gnupg.org/AgentForwarding) for more information.

Import the public key on the remote host. On the local host, copy the public keyring to the remote host:

```console
scp ~/.gnupg/pubring.kbx remote:~/.gnupg/
```

On modern distributions, such as Fedora 30, there is no need to set `RemoteForward` in `~/.ssh/config`

### Legacy distributions

On the local host, run:

```console
gpgconf --list-dirs agent-extra-socket
```

This should return a path to agent-extra-socket - `/run/user/1000/gnupg/S.gpg-agent.extra` - though on older Linux distros (and macOS) it may be `/home/<user>/.gnupg/S/gpg-agent.extra`

Find the agent socket on the **remote** host:

```console
gpgconf --list-dirs agent-socket
```

This should return a path such as `/run/user/1000/gnupg/S.gpg-agent`

Finally, enable agent forwarding for a given host by adding the following to the local host's `~/.ssh/config` (agent sockets may differ):

```
Host
  Hostname remote-host.tld
  StreamLocalBindUnlink yes
  RemoteForward /run/user/1000/gnupg/S.gpg-agent /run/user/1000/gnupg/S.gpg-agent.extra
  #RemoteForward [remote socket] [local socket]
```

It may be necessary to edit `gpg-agent.conf` on the *local* host to add the following information:

```
pinentry-program /usr/bin/pinentry-gtk-2
extra-socket /run/user/1000/gnupg/S.gpg-agent.extra
```

> [!IMPORTANT]
> The pinentry program starts on the *local* host, not remote.

Any pinentry program except `pinentry-tty` or `pinentry-curses` may be used. This is because local `gpg-agent` may start headlessly (by systemd without `$GPG_TTY` set locally telling which tty it is on), thus failed to obtain the pin. Errors on the remote may be misleading saying that there is *IO Error*. (Yes, internally there is actually an *IO Error* since it happens when writing to/reading from tty while finding no tty to use, but for end users this is not friendly.)

See [Issue 85](https://github.com/drduh/YubiKey-Guide/issues/85) for more information and troubleshooting.

### Chained GnuPG agent forwarding

Assume you have gone through the steps above and have `S.gpg-agent` on the *remote*, and you would like to forward this agent into a *third* box, first you may need to configure `sshd_config` of *third* in the same way as *remote*, then in the ssh config of *remote*, add the following lines:

```console
Host third
  Hostname third-host.tld
  StreamLocalBindUnlink yes
  RemoteForward /run/user/1000/gnupg/S.gpg-agent /run/user/1000/gnupg/S.gpg-agent
  #RemoteForward [remote socket] [local socket]
```

You should change the path according to `gpgconf --list-dirs agent-socket` on *remote* and *third*.

On *local* you have `S.gpg-agent.extra` whereas on *remote* and *third*, you only have `S.gpg-agent`

## Using multiple YubiKeys

When a GnuPG key is added to YubiKey using `keytocard`, the key is deleted from the keyring and a **stub** is added, pointing to the YubiKey. The stub identifies the GnuPG key ID and YubiKey serial number.

When a Subkey is added to an additional YubiKey, the stub is overwritten and will now point to the latest YubiKey. GnuPG will request a specific YubiKey by serial number, as referenced by the stub, and will not recognize another YubiKey with a different serial number.

To scan an additional YubiKey and recreate the correct stub:

```console
gpg-connect-agent "scd serialno" "learn --force" /bye
```

Alternatively, use a script to delete the GnuPG shadowed key, where the serial number is stored (see [GnuPG #T2291](https://dev.gnupg.org/T2291)):

```console
cat >> ~/scripts/remove-keygrips.sh <<EOF
#!/usr/bin/env bash
(( $# )) || { echo "Specify a key." >&2; exit 1; }
KEYGRIPS=$(gpg --with-keygrip --list-secret-keys "$@" | awk '/Keygrip/ { print $3 }')
for keygrip in $KEYGRIPS
do
    rm "$HOME/.gnupg/private-keys-v1.d/$keygrip.key" 2> /dev/null
done

gpg --card-status
EOF

chmod +x ~/scripts/remove-keygrips.sh

~/scripts/remove-keygrips.sh $KEYID
```

See discussion in Issues [#19](https://github.com/drduh/YubiKey-Guide/issues/19) and [#112](https://github.com/drduh/YubiKey-Guide/issues/112) for more information and troubleshooting steps.

## Email

YubiKey can be used to decrypt and sign emails and attachments using [Thunderbird](https://www.thunderbird.net/), [Enigmail](https://www.enigmail.net) and [Mutt](http://www.mutt.org/). Thunderbird supports OAuth 2 authentication and can be used with Gmail. See [this EFF guide](https://ssd.eff.org/en/module/how-use-pgp-linux) for more information. Mutt has OAuth 2 support since version 2.0.

### Thunderbird

Follow [instructions on the mozilla wiki](https://wiki.mozilla.org/Thunderbird:OpenPGP:Smartcards#Configure_an_email_account_to_use_an_external_GnuPG_key) to setup your YubiKey with your thunderbird client using the external gpg provider.

> [!NOTE]
> Thunderbird will [fail](https://github.com/drduh/YubiKey-Guide/issues/448) to decrypt emails if the ASCII `armor` option is enabled in `gpg.conf`. If you see the error `gpg: [don't know]: invalid packet (ctb=2d)` or `message cannot be decrypted (there are unknown problems with this encrypted message)` simply remove this option.

### Mailvelope

[Mailvelope](https://www.mailvelope.com/en) allows YubiKey to be used with Gmail and others.

> [!NOTE]
> Mailvelope [does not work](https://github.com/drduh/YubiKey-Guide/issues/178) with the `throw-keyids` option set in `gpg.conf`

On macOS, install gpgme using Homebrew:

```console
brew install gpgme
```

To allow Chrome to run gpgme, edit `~/Library/Application\ Support/Google/Chrome/NativeMessagingHosts/gpgmejson.json` to add:

```json
{
    "name": "gpgmejson",
    "description": "Integration with GnuPG",
    "path": "/usr/local/bin/gpgme-json",
    "type": "stdio",
    "allowed_origins": [
        "chrome-extension://kajibbejlbohfaggdiogboambcijhkke/"
    ]
}
```

Edit the default path to allow Chrome to find GnuPG:

```console
sudo launchctl config user path /usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin
```

Finally, install the [Mailvelope extension](https://chromewebstore.google.com/detail/mailvelope/kajibbejlbohfaggdiogboambcijhkke) from the Chrome web store.

### Mutt

Mutt has both CLI and TUI interfaces - the latter provides powerful functions for processing email. In addition, PGP can be integrated such that cryptographic operations can be done without leaving TUI.

To enable GnuPG support, copy `/usr/share/doc/mutt/samples/gpg.rc`

Edit the file to enable options `pgp_default_key`, `pgp_sign_as` and `pgp_autosign`

`source` the file in `muttrc`

> [!NOTE]
> `pinentry-tty` set as the pinentry program (in `gpg-agent.conf`) is reported to cause problems with Mutt TUI, because it uses curses; use `pinentry-curses` or other graphic pinentry program instead.

## Keyserver

Public keys can be uploaded to a public server for discoverability:

```console
gpg --send-key $KEYID

gpg --keyserver keys.gnupg.net --send-key $KEYID

gpg --keyserver hkps://keyserver.ubuntu.com:443 --send-key $KEYID
```

Or if [uploading to keys.openpgp.org](https://keys.openpgp.org/about/usage):

```console
gpg --send-key $KEYID | curl -T - https://keys.openpgp.org
```

The public key URL can also be added to YubiKey (based on [Shaw 2003](https://datatracker.ietf.org/doc/html/draft-shaw-openpgp-hkp-00)):

```console
URL="hkps://keyserver.ubuntu.com:443/pks/lookup?op=get&search=${KEYID}"
```

Edit YubiKey with `gpg --edit-card` and the Admin PIN:

```console
gpg/card> admin

gpg/card> url
URL to retrieve public key: hkps://keyserver.ubuntu.com:443/pks/lookup?op=get&search=0xFF00000000000000

gpg/card> quit
```

# Updating keys

PGP does not provide [forward secrecy](https://en.wikipedia.org/wiki/Forward_secrecy), meaning a compromised key may be used to decrypt all past messages. Although keys stored on YubiKey are more difficult to exploit, it is not impossible: the key and PIN could be physically compromised, or a vulnerability may be discovered in firmware or in the random number generator used to create keys, for example. Therefore, it is recommended practice to rotate Subkeys periodically.

When a Subkey expires, it can either be renewed or replaced. Both actions require access to the Certify key.

- Renewing Subkeys by updating expiration indicates continued custody of the Certify key and is generally more convenient.

- Replacing Subkeys is less convenient, but potentially more secure: new Subkeys will **not** be able to decrypt previous messages, nor authenticate with SSH, etc. Recipients will need the updated public key. Any encrypted secrets must be decrypted and re-encrypted to new Subkeys. This process is functionally equivalent to losing the YubiKey and provisioning a new one.

Neither rotation method is superior and it is up to personal philosophy on identity management and individual threat modeling to decide which one to use, or whether to expire Subkeys at all. Ideally, Subkeys would be ephemeral: used only once for each unique encryption, signature and authentication event, however in practice that is not really practical nor worthwhile with YubiKey. Advanced users may dedicate an air-gapped machine for frequent credential rotation.

To renew or rotate Subkeys, follow the same process as generating keys: boot to a secure environment, install required software and disable networking.

Connect the portable storage device with the Certify key and identify the disk label.

Decrypt and mount the encrypted volume:

```console
sudo cryptsetup luksOpen /dev/sdc1 gnupg-secrets

sudo mkdir /mnt/encrypted-storage

sudo mount /dev/mapper/gnupg-secrets /mnt/encrypted-storage
```

Mount the non-encrypted public partition:

```console
sudo mkdir /mnt/public

sudo mount /dev/sdc2 /mnt/public
```

Copy the original private key materials (after updating the encrypted storage directory name) to a temporary working directory:

```console
export GNUPGHOME=$(mktemp -d -t $(date +%Y.%m.%d)-XXXX)

cp -avi /mnt/encrypted-storage/2025.12.31-AbCd/* $GNUPGHOME/
```

Confirm the identity is available, set the key id and fingerprint:

```console
gpg -K

export KEYID=$(gpg -k --with-colons "$IDENTITY" | \
    awk -F: '/^pub:/ { print $5; exit }')

export KEYFP=$(gpg -k --with-colons "$IDENTITY" | \
    awk -F: '/^fpr:/ { print $10; exit }')

echo $KEYID $KEYFP
```

Recall the Certify key passphrase and set it, for example:

```console
export CERTIFY_PASS=ABCD-0123-IJKL-4567-QRST-UVWX
```

## Renew Subkeys

Set the updated expiration date:

```console
export EXPIRATION=2027-09-01
```

Renew the Subkeys:

```console
echo "$CERTIFY_PASS" | \
    gpg --batch --pinentry-mode=loopback \
        --passphrase-fd 0 --quick-set-expire "$KEYFP" "$EXPIRATION" \
    $(gpg -K --with-colons | awk -F: '/^fpr:/ { print $10 }' | tail -n "+2" | tr "\n" " ")
```

Export the updated public key:

```console
gpg --armor --export $KEYID | sudo tee /mnt/public/$KEYID-$(date +%F).asc
```

Transfer the public key to the destination host and import it:

```console
gpg --import /mnt/public/*.asc
```

Alternatively, publish to a public key server and download it:

```console
gpg --send-key $KEYID

gpg --recv $KEYID
```

The validity of the GnuPG identity will be extended, allowing it to be used again for encryption and signature operations.

The SSH public key does **not** need to be updated on remote hosts.

## Rotate Subkeys

Follow the original procedure to [Create Subkeys](#create-subkeys).

Previous Subkeys can be deleted from the identity.

Finish by transfering new Subkeys to YubiKey.

Copy the **new** temporary working directory to encrypted storage, which is still mounted:

```console
sudo cp -avi $GNUPGHOME /mnt/encrypted-storage
```

Unmount and close the encrypted volume:

```console
sudo umount /mnt/encrypted-storage

sudo cryptsetup luksClose gnupg-secrets
```

Export the updated public key:

```console
sudo mkdir /mnt/public

sudo mount /dev/sdc2 /mnt/public

gpg --armor --export $KEYID | sudo tee /mnt/public/$KEYID-$(date +%F).asc

sudo umount /mnt/public
```

Remove the storage device and follow the original steps to transfer new Subkeys (`4`, `5` and `6`) to YubiKey, replacing existing ones.

Reboot or securely erase the GnuPG temporary working directory.

# Reset YubiKey

If PIN attempts are exceeded, the YubiKey is locked and must be [Reset](https://developers.yubico.com/ykneo-openpgp/ResetApplet.html) and set up again using the encrypted backup.

Copy the following to a file and run `gpg-connect-agent -r $file`, then re-insert the YubiKey to complete reset.

```console
/hex
scd serialno
scd apdu 00 20 00 81 08 40 40 40 40 40 40 40 40
scd apdu 00 20 00 81 08 40 40 40 40 40 40 40 40
scd apdu 00 20 00 81 08 40 40 40 40 40 40 40 40
scd apdu 00 20 00 81 08 40 40 40 40 40 40 40 40
scd apdu 00 20 00 83 08 40 40 40 40 40 40 40 40
scd apdu 00 20 00 83 08 40 40 40 40 40 40 40 40
scd apdu 00 20 00 83 08 40 40 40 40 40 40 40 40
scd apdu 00 20 00 83 08 40 40 40 40 40 40 40 40
scd apdu 00 e6 00 00
scd apdu 00 44 00 00
/echo Card has been successfully reset.
/bye
```

Or use `ykman` (sometimes in `~/.local/bin/`):

```console
$ ykman openpgp reset
WARNING! This will delete all stored OpenPGP keys and data and restore factory settings? [y/N]: y
Resetting OpenPGP data, don't remove your YubiKey...
Success! All data has been cleared and default PINs are set.
PIN:         123456
Reset code:  NOT SET
Admin PIN:   12345678
```

# Optional hardening

The following steps may improve the security and privacy of YubiKey.

## Improving entropy

Generating cryptographic keys requires high-quality [randomness](https://www.random.org/randomness/), measured as entropy. Most operating systems use software-based pseudorandom number generators or CPU-based hardware random number generators (HRNG).

Optionally, a device such as [OneRNG](https://onerng.info/onerng/) may be used to [increase the speed](https://lwn.net/Articles/648550/) and possibly the quality of available entropy.

Before creating keys, configure [rng-tools](https://wiki.archlinux.org/title/Rng-tools):

```console
sudo apt -y install at rng-tools python3-gnupg openssl

wget https://github.com/OneRNG/onerng.github.io/raw/master/sw/onerng_3.7-1_all.deb
```

Verify the package:

```console
sha256sum onerng_3.7-1_all.deb
```

The value must match:

```console
b7cda2fe07dce219a95dfeabeb5ee0f662f64ba1474f6b9dddacc3e8734d8f57
```

Install the package:

```console
sudo dpkg -i onerng_3.7-1_all.deb

echo "HRNGDEVICE=/dev/ttyACM0" | sudo tee /etc/default/rng-tools
```

Insert the device and restart rng-tools:

```console
sudo atd

sudo service rng-tools restart
```

## Enable KDF

> [!IMPORTANT]
> This feature may not be compatible with older GnuPG versions, especially mobile clients. These incompatible clients will not function because the PIN will always be rejected.

This step must be completed before changing PINs or moving keys or an error will occur: `gpg: error for setup KDF: Conditions of use not satisfied`

Key Derived Function (KDF) enables YubiKey to store the hash of PIN, preventing the PIN from being passed as plain text.

Enable KDF using the default Admin PIN of `12345678`:

```console
gpg --command-fd=0 --pinentry-mode=loopback --card-edit <<EOF
admin
kdf-setup
12345678
EOF
```

## Network considerations

This section is primarily focused on Debian / Ubuntu based systems, but the same concept applies to any system connected to a network.

Whether you're using a VM, installing on dedicated hardware, or running a Live OS temporarily, start *without* a network connection and disable any unnecessary services listening on all interfaces before connecting to the network.

The reasoning for this is because services like cups or avahi can be listening by default. While this isn't an immediate problem it simply broadens the attack surface. Not everyone will have a dedicated subnet or trusted network equipment they can control, and for the purposes of this guide, these steps treat *any* network as untrusted / hostile.

**Disable listening services**

- Ensures only essential network services are running
- If the service doesn't exist you'll get a "Failed to stop" which is fine
- Only disable `Bluetooth` if you don't need it

```bash
sudo systemctl stop bluetooth exim4 cups avahi avahi-daemon sshd
```

**Firewall**

Enable a basic firewall policy of *deny inbound, allow outbound*. Note that Debian does not come with a firewall, simply disabling the services in the previous step is fine. The following options have Ubuntu and similar systems in mind.

On Ubuntu, `ufw` is built in and easy to enable:

```bash
sudo ufw enable
```

On systems without `ufw`, `nftables` is replacing `iptables`. The [nftables wiki has examples](https://wiki.nftables.org/wiki-nftables/index.php/Simple_ruleset_for_a_workstation) for a baseline *deny inbound, allow outbound* policy. The `fw.inet.basic` policy covers both IPv4 and IPv6.

(Remember to download this README and any other resources to another external drive when creating the bootable media, to have this information ready to use offline)

Regardless of which policy you use, write the contents to a file (e.g. `nftables.conf`) and apply the policy with the following comand:

```bash
sudo nft -f ./nftables.conf
```

**Review system state**

`NetworkManager` should be the only listening service on port 68/udp to obtain a DHCP lease (and 58/icmp6 if you have IPv6).

If you want to look at every process's command line arguments you can use `ps axjf`. This prints a process tree which may have a large number of lines but should be easy to read on a live image or fresh install.

```bash
sudo ss -anp -A inet    # Dump all network state information
ps axjf                 # List all processes in a process tree
ps aux                  # BSD syntax, list all processes but no process tree
```

If you find any additional processes listening on the network that aren't needed, take note and disable them with one of the following:

```bash
sudo systemctl stop <process-name>                      # Stops services managed by systemctl
sudo pkill -f '<process-name-or-command-line-string>'   # Terminate the process by matching it's command line string
pgrep -f '<process-name-or-command-line-string>'        # Obtain the PID
sudo kill <pid>                                         # Terminate the process via its PID
```

Now connect networking.

# Notes

1. YubiKey has two configurations, invoked with either a short or long press. By default, the short-press mode is configured for HID OTP; a brief touch will emit an OTP string starting with `cccccccc`. OTP mode can be swapped to the second configuration via the YubiKey Personalization tool or disabled entirely using [YubiKey Manager](https://developers.yubico.com/yubikey-manager): `ykman config usb -d OTP`

1. Using YubiKey for GnuPG does not prevent use of [other features](https://developers.yubico.com/), such as [WebAuthn](https://developers.yubico.com/WebAuthn/) and [OTP](https://developers.yubico.com/OTP/).

1. Add additional identities to a Certify key with the `adduid` command during setup, then trust it ultimately with `trust` and `5` to configure for use.

1. To switch between YubiKeys, remove the first YubiKey and restart gpg-agent, ssh-agent and pinentry with `pkill "gpg-agent|ssh-agent|pinentry" ; eval $(gpg-agent --daemon --enable-ssh-support)` then insert the other YubiKey and run `gpg-connect-agent updatestartuptty /bye`

1. To use YubiKey on multiple computers, import the corresponding public keys, then confirm YubiKey is visible with `gpg --card-status`. Trust the imported public keys ultimately with `trust` and `5`, then `gpg --list-secret-keys` will show the correct and trusted key.

# Troubleshooting

- Use `man gpg` to understand GnuPG options and command-line flags.

- To get more information on potential errors, restart the `gpg-agent` process with debug output to the console with `pkill gpg-agent; gpg-agent --daemon --no-detach -v -v --debug-level advanced --homedir ~/.gnupg`.

- A lot of issues can be fixed by removing and re-inserting YubiKey, or restarting the `gpg-agent` process.

- If you receive the error, `Yubikey core error: no yubikey present` - make sure the YubiKey is inserted correctly. It should blink once when plugged in.

- If you still receive the error, `Yubikey core error: no yubikey present` - you likely need to install newer versions of yubikey-personalize as outlined in [Install software](#install-software).

- If you see `General key info..: [none]` in card status output - import the public key.

- If you receive the error, `gpg: decryption failed: secret key not available` - you likely need to install GnuPG version 2.x. Another possibility is that there is a problem with the PIN, e.g., it is too short or blocked.

- If you receive the error, `Yubikey core error: write error` - YubiKey is likely locked. Install and run yubikey-personalization-gui to unlock it.

- If you receive the error, `Key does not match the card's capability` - you likely need to use 2048-bit RSA key sizes.

- If you receive the error, `sign_and_send_pubkey: signing failed: agent refused operation` - make sure you replaced `ssh-agent` with `gpg-agent` as noted above.

- If you still receive the error, `sign_and_send_pubkey: signing failed: agent refused operation` - [run the command](https://bugs.debian.org/cgi-bin/bugreport.cgi?bug=835394) `gpg-connect-agent updatestartuptty /bye`

- If you still receive the error, `sign_and_send_pubkey: signing failed: agent refused operation` - edit `~/.gnupg/gpg-agent.conf` to set a valid `pinentry` program path. `gpg: decryption failed: No secret key` could also indicate an invalid `pinentry` path

- If you still receive the error, `sign_and_send_pubkey: signing failed: agent refused operation` - it is a [known issue](https://bbs.archlinux.org/viewtopic.php?id=274571) that openssh 8.9p1 and higher has issues with YubiKey. Adding `KexAlgorithms -sntrup761x25519-sha512@openssh.com` to `/etc/ssh/ssh_config` often resolves the issue.

- If you receive the error, `The agent has no identities` from `ssh-add -L`, make sure you have installed and started `scdaemon`

- If you receive the error, `Error connecting to agent: No such file or directory` from `ssh-add -L`, the UNIX file socket that the agent uses for communication with other processes may not be set up correctly. On Debian, try `export SSH_AUTH_SOCK="/run/user/$UID/gnupg/S.gpg-agent.ssh"`. Also see that `gpgconf --list-dirs agent-ssh-socket` is returning single path, to existing `S.gpg-agent.ssh` socket.

- If you receive the error, `Permission denied (publickey)`, increase ssh verbosity with the `-v` flag and verify the public key from the card is being offered: `Offering public key: RSA SHA256:abcdefg... cardno:00060123456`. If it is, verify the correct user the target system - not the user on the local system. Otherwise, be sure `IdentitiesOnly` is not [enabled](https://github.com/FiloSottile/whosthere#how-do-i-stop-it) for this host.

- If SSH authentication still fails - add up to 3 `-v` flags to the `ssh` command to increase verbosity.

- If it still fails, it may be useful to stop the background `sshd` daemon process service on the server (e.g. using `sudo systemctl stop sshd`) and instead start it in the foreground with extensive debugging output, using `/usr/sbin/sshd -eddd`. Note that the server will not fork and will only process one connection, therefore has to be re-started after every `ssh` test.

- If you receive the error, `Please insert the card with serial number` see [Using Multiple Keys](#using-multiple-keys).

- If you receive the error, `There is no assurance this key belongs to the named user` or `encryption failed: Unusable public key` or `No public key` use `gpg --edit-key` to set `trust` to `5 = I trust ultimately`

- If, when you try the above command, you get the error `Need the secret key to do this` - specify trust for the key in `~/.gnupg/gpg.conf` by using the `trust-key [key ID]` directive.

- If, when using a previously provisioned YubiKey on a new computer with `pass`, you see the following error on `pass insert`, you need to adjust the trust associated with the key. See the note above.

```
gpg: 0x0000000000000000: There is no assurance this key belongs to the named user
gpg: [stdin]: encryption failed: Unusable public key
```

- If you receive the error, `gpg: 0x0000000000000000: skipped: Unusable public key`, `signing failed: Unusable secret key`, or `encryption failed: Unusable public key` the Subkey may be expired and can no longer be used to encrypt nor sign messages. It can still be used to decrypt and authenticate, however.

- If the _pinentry_ graphical dialog does not show and this error appears: `sign_and_send_pubkey: signing failed: agent refused operation`, install the `dbus-user-session` package and restart for the `dbus` user session to be fully inherited. This is because `pinentry` complains about `No $DBUS_SESSION_BUS_ADDRESS found`, falls back to `curses` but doesn't find the expected `tty`

- If, when you try the above `--card-status` command, you get receive the error, `gpg: selecting card failed: No such device` or `gpg: OpenPGP card not available: No such device`, it's possible that the latest release of pcscd now requires polkit rules to operate properly. Create the following file to allow users in the `wheel` group to use the card. Be sure to restart pcscd when you're done to allow the new rules to take effect.

```console
cat << EOF >  /etc/polkit-1/rules.d/99-pcscd.rules
polkit.addRule(function(action, subject) {
        if (action.id == "org.debian.pcsc-lite.access_card" &&
                subject.isInGroup("wheel")) {
                return polkit.Result.YES;
        }
});
polkit.addRule(function(action, subject) {
        if (action.id == "org.debian.pcsc-lite.access_pcsc" &&
                subject.isInGroup("wheel")) {
                return polkit.Result.YES;
        }
});
EOF
```

- If the public key is lost, follow [this guide](https://www.nicksherlock.com/2021/08/recovering-lost-gpg-public-keys-from-your-yubikey/) to recover it from YubiKey.

- Refer to Yubico article [Troubleshooting Issues with GPG](https://support.yubico.com/hc/en-us/articles/360013714479-Troubleshooting-Issues-with-GPG) for additional guidance.

# Alternative solutions

* [`vorburger/ed25519-sk.md`](https://github.com/vorburger/vorburger.ch-Notes/blob/develop/security/ed25519-sk.md) - use YubiKey for SSH without GnuPG
* [`smlx/piv-agent`](https://github.com/smlx/piv-agent) - SSH and GnuPG agent which can be used with PIV devices
* [`keytotpm`](https://www.gnupg.org/documentation/manuals/gnupg/OpenPGP-Key-Management.html) - use GnuPG with TPM systems

# Additional resources

* [Yubico - PGP](https://developers.yubico.com/PGP/)
* [Yubico - Yubikey Personalization](https://developers.yubico.com/yubikey-personalization/)
* [A Visual Explanation of GPG Subkeys (2022)](https://rgoulter.com/blog/posts/programming/2022-06-10-a-visual-explanation-of-gpg-subkeys.html)
* [dhess/nixos-yubikey](https://github.com/dhess/nixos-yubikey)
* [lsasolutions/makegpg](https://gitlab.com/lsasolutions/makegpg)
* [Trammell Hudson - Yubikey (2020)](https://trmm.net/Yubikey)
* [Yubikey forwarding SSH keys (2019)](https://blog.onefellow.com/post/180065697833/yubikey-forwarding-ssh-keys)
* [GPG Agent Forwarding (2018)](https://mlohr.com/gpg-agent-forwarding/)
* [Stick with security: YubiKey, SSH, GnuPG, macOS (2018)](https://evilmartians.com/chronicles/stick-with-security-yubikey-ssh-gnupg-macos)
* [PGP and SSH keys on a Yubikey NEO (2015)](https://www.esev.com/blog/post/2015-01-pgp-ssh-key-on-yubikey-neo/)
* [Offline GnuPG Master Key and Subkeys on YubiKey NEO Smartcard (2014)](https://blog.josefsson.org/2014/06/23/offline-gnupg-master-key-and-subkeys-on-yubikey-neo-smartcard/)
* [Creating the perfect GPG keypair (2013)](https://alexcabal.com/creating-the-perfect-gpg-keypair/)

[^1]: Use single quotes to wrap double quote character(s) (`"`) - `export IDENTITY='My Identity (a.k.a. "YubiKey User") <yubikey@example.domain>'`
[^2]: [Revocation certificates](https://security.stackexchange.com/questions/14718/does-openpgp-key-expiration-add-to-security/79386#79386) should be used to revoke an identity.
[^3]: See [issue 477](https://github.com/drduh/YubiKey-Guide/issues/477) for NIST guideline discussion.
