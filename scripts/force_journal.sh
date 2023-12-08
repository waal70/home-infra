#! /bin/sh
echo u > /proc/sysrq-trigger 
echo s > /proc/sysrq-trigger 
tune2fs -O ^has_journal /dev/sda1 
e2fsck -fy /dev/sda1 
echo s > /proc/sysrq-trigger 
#echo b > /proc/sysrq-trigger
