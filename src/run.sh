#!/bin/sh

DIR="$(cd "$(dirname "$0")" && pwd)"
cd $DIR

nohup python3 -u startup.py "$@" >> /tmp/karen.log 2>> /tmp/karen.log &

exit
