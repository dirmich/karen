#!/bin/sh

DIR="$(cd "$(dirname "$0")" && pwd)"
cd $DIR

wget -c https://github.com/mozilla/DeepSpeech/releases/download/v0.8.0/deepspeech-0.8.0-models.pbmm
wget -c https://github.com/mozilla/DeepSpeech/releases/download/v0.8.0/deepspeech-0.8.0-models.tflite
wget -c https://github.com/mozilla/DeepSpeech/releases/download/v0.8.0/deepspeech-0.8.0-models.scorer
