#!/bin/sh

DIR="$(cd "$(dirname "$0")" && pwd)"
cd $DIR

wget -c https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml
