#!/bin/bash

socat - UNIX-CONNECT:/tmp/tgmount.socket | jq '.caches'