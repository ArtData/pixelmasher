#!/usr/bin/env python
import json, urllib2, sys

l = json.load(open(sys.argv[1]))

for i in l:
    im = i['image']
    if im:
        f = 'urls/' + urllib2.quote(im, '') + '.jpeg'
        open(f, 'wb').write('')
