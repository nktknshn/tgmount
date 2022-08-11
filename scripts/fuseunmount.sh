#!/bin/bash

MOUNTS=$(mount | grep test_tgmount | cut -d' ' -f3)

if [[ "$MOUNTS" == "" ]]; then
    echo no test_tgmount mounts
    exit
fi

for var in "$MOUNTS"
do
    echo "$var"
    fusermount -u -z "$var"
done
