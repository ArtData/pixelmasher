#!/bin/sh

mkdir -p downloads
mkdir -p completed
mkdir -p failed

while true; do
    python sum_images.py
    sleep 2400
done
