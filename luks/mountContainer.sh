#!/bin/bash

# This script will protect your secret repository by making the mountpoint a LUKS encrypted container.
# Prerequisites:
# .luks_passphrase in HOMEA
# .yubikey_challenge in HOMEA
# Both should have been made with "echo -n > .luks_passphrase" and "echo -n > .yubikey_challenge"
# Remember to escape any special characters in the passphrase file.

set -e

# Configurable variables
HOMEA=/home/awaal
SCRIPTHOME="${HOMEA}/ansible/home-infra/luks"
USER=awaal
IMG_NAME="${HOMEA}/container.img"
IMG_SIZE="1G"
MOUNT_DIR="${HOMEA}/ansible/home"
LOOP_DEV=""
LUKS_NAME="container_luks"
YUBI_SLOT="2"  # Change as needed
PASSPHRASE_FILE="${HOMEA}/.luks_passphrase"  # File containing slot 0 passphrase
CHALLENGE_FILE="${HOMEA}/.yubikey_challenge"
TEMP_KEY="1234"

MOUNTONLY=0

# While debugging, remove img file to start fresh
# rm -f "$IMG_NAME"

# Check if first argument is "UNDO"; if so, unmount and close LUKS container
if [ "$1" == "UNDO" ]; then
    echo "Unmounting and closing LUKS container..."
    if mountpoint -q "$MOUNT_DIR"; then
        umount "$MOUNT_DIR"
        echo "Unmounted $MOUNT_DIR"
        rm -rf "$MOUNT_DIR"
    else
        echo "$MOUNT_DIR is not mounted."
    fi
    if [ -e "/dev/mapper/$LUKS_NAME" ]; then
        cryptsetup close "$LUKS_NAME"
        echo "Closed LUKS container $LUKS_NAME"
    else
        echo "/dev/mapper/$LUKS_NAME is not active."
    fi
    echo "Removed mount point and closed container if they were active."
    if [ -f "$IMG_NAME" ]; then
        echo "Image file $IMG_NAME remains."
    fi
    exit 0
fi

# Check for .img file
if [ ! -f "$IMG_NAME" ]; then
    echo "Image file not found. Creating $IMG_NAME..."
    fallocate -l "$IMG_SIZE" "$IMG_NAME"
else
    echo "Image file $IMG_NAME found."
    let "MOUNTONLY=MOUNTONLY+1"
fi


# Check if already LUKS formatted
if ! cryptsetup isLuks "$IMG_NAME"; then
    echo "Formatting with LUKS..."
    cryptsetup luksFormat "$IMG_NAME" --key-file "$PASSPHRASE_FILE" --batch-mode
else
    echo "LUKS formatting already present."
    let "MOUNTONLY=MOUNTONLY+1"
fi

echo "MOUNTONLY is $MOUNTONLY"

# Check if /dev/mapper/$LUKS_NAME is already open
if [ -e "/dev/mapper/$LUKS_NAME" ]; then
    echo "/dev/mapper/$LUKS_NAME is already there. This probably means everything is active."
    exit 0
fi

# Check if mount directory is already mounted
if mountpoint -q "$MOUNT_DIR"; then
    echo "$MOUNT_DIR is already mounted. This probably means everything is active."
    exit 0
fi

if [ "$MOUNTONLY" -eq 2 ]; then
    echo "Both image file and LUKS formatting already present. Skipping enrollment of YubiKey."

else
    echo "Continuing with setting up LUKS container..."

    # Check if key slot $YUBI_SLOT is already in use
    # if cryptsetup luksDump "$IMG_NAME" | awk "/^Keyslots:/ {found=1} found && /^\s*$YUBI_SLOT:/ {getline; if (\$0 ~ /ENABLED/) exit 0; else exit 1}"; then
    #     echo "Key slot $YUBI_SLOT is already in use. Exiting."
    #     exit 1
    # fi

    # Adding additional keyslot for YubiKey
    echo "Pre-allocating keyslot $YUBI_SLOT for YubiKey..."
    echo "$TEMPKEY" | cryptsetup luksAddKey --key-slot "$YUBI_SLOT" --key-file "$PASSPHRASE_FILE" "$IMG_NAME" --batch-mode

    # Enroll YubiKey (requires ykman and cryptsetup with yubikey support)
    echo "Enrolling YubiKey..."
    # First argument: name of passphrase file
    # Second argument: name of yubikey challenge file
    # Third argument: name of container image
    # Fourth argument: the number of the key-slot
    expect -f "$SCRIPTHOME"/enroll_yubikey.exp "$PASSPHRASE_FILE" "$CHALLENGE_FILE" "$IMG_NAME" "$YUBI_SLOT"
fi

# Open LUKS container using YubiKey
echo "Attempting to open LUKS container with YubiKey using " $CHALLENGE_FILE"..."
# First argument: name of yubikey challenge file
# Second argument: name of container image
# Third argument: name of the mount under dev/mapper
expect -f "$SCRIPTHOME"/open_with_yubikey.exp "$CHALLENGE_FILE" "$IMG_NAME" "$LUKS_NAME"

# Create ext4 filesystem if not already present
if ! blkid | grep -q "$LUKS_NAME"; then
    echo "Creating ext4 filesystem..."
    mkfs.ext4 "/dev/mapper/$LUKS_NAME"
fi

# Create mount directory if it doesn't exist
if [ ! -d "$MOUNT_DIR" ]; then
    echo "Creating mount directory $MOUNT_DIR..."
    mkdir -p "$MOUNT_DIR"
fi

# Mount the container
mount "/dev/mapper/$LUKS_NAME" "$MOUNT_DIR"
# Ensure mount directory is user-owned
chown -R "$USER":"$USER" "$MOUNT_DIR"
echo "Container mounted at $MOUNT_DIR"
