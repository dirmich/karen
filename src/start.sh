#!/bin/sh

DIR="$(cd "$(dirname "$0")" && pwd)"
cd $DIR

export DISPLAY=:0
python3.7 ./karen.py "$@" \
	--listener-start \
	--speaker-start \
	--watcher-start \
	--brain-start \
	--speaker-visualizer '["xterm","-e","vis"]' \
	--watcher-trained ~/faces.yml \
	--watcher-input-folder ~/Pictures/faces
