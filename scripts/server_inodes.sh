#!/bin/bash

socat - UNIX-CONNECT:/tmp/tgmount.socket | jq -r '.fs.inodes | .[] | .[1]'