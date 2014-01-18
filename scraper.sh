#!/bin/sh

while true; do
    # Disabling SSL and cross-site security is needed when using the built-in async downloader.
    # Disabling image loading speeds things up a lot, and we can still scrape imgrc URLs.
    # Run this in a subshell with timeout.

    casperjs --ignore-ssl-errors=yes --web-security=no --verbose --load-images=false scraper.js \
        2>&1 | grep -v "CoreText performance note"
    sleep 5
done
