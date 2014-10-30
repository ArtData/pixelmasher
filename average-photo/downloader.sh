#!/bin/sh

mkdir -p urls
mkdir -p downloads
mkdir -p failed

while true; do
    node downloader.js
    sleep 2
done
