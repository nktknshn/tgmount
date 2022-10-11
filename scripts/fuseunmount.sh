#!/bin/bash

MOUNTS=$(mount | grep "test_tgmount on" | cut -d' ' -f3)

if [[ "$MOUNTS" == "" ]]; then
    echo no test_tgmount mounts
    exit
fi

for var in $MOUNTS
do
    #echo "$var"
    fusermount3 -u -z "$var"
done
