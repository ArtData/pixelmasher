#!/bin/sh
#
# Quick backup to dropbox, without including the whole dataset.
#

DEST=~/Dropbox/art/2014/01jan/average_photo

# Account for how many files we have, but don't back them all up
(for n in downloads failed completed; do echo $n; ls $n | wc -l; done) | tee stats.txt

# Full file listing, for reference
ls -lR > listing.txt

# Copy all the small stuff
cp *.sh *.js *.py *.jpg *.tiff *.txt $DEST

# Compress the latest sum buffer
gzip -c < sum.npy > $DEST/sum.npy.gz
