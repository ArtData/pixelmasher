import json, urllib2

l = json.load(open('download.json'))

for i in l:
    im = i['image']
    if im:
        f = 'urls/' + urllib2.quote(im, '') + '.jpeg'
        open(f, 'wb').write('')
