/*
 * Google Image Search scraper for CasperJS
 *
 * Micah Elizabeth Scott <micah@scanlime.org>
 */

var casper = require('casper').create();
var fs = require('fs');

// Different ways to get randomish results..

var term1 = [
    ('' + Math.random()).substr(4, 2),
    'site:flickr.com',
    'site:facebook.com',
    'site:yahoo.com',
    'site:imgur.com',
    'site:twitter.com',
    'site:reddit.com',
    'site:blogspot.com',
    'site:wordpress.com',
    'site:pinterest.com',
    'site:tumblr.com',
    'site:blogger.com',
    'site:livejournal.com',
    'site:photobucket.com',
    'site:deviantart.com',
    'site:shutterfly.com',
    'site:imageshack.us',
    'site:tinypic.com',
    'site:imagevenue.com',
    'site:weheartit.com',
    'site:smugmug.com',
    'site:twitpic.com',
    'site:4chan.org',
    'site:snapfish.com',
    'site:picasa.google.com',
];

var term2 = [
    '',
    '+' + ('' + Math.random()).substr(4, 1),
    '+.',
    '+_',
    '+photo',
    '+' + ('' + Math.random()).substr(4, 2),
    '+' + ('' + Math.random()).substr(4, 3),
    '+' + ((Math.random() * 1e9) & 0xFF).toString(16),
    '+' + ((Math.random() * 1e9) & 0xFFF).toString(16),
    '+' + ((Math.random() * 1e9) & 0xFFFF).toString(16),
    '+' + ((Math.random() * 1e9) & 0xFFFFF).toString(16),
];

var query = choice(term1) + choice(term2);

//////////////

var url = 'https://www.google.com/search?q=' + query + '&tbs=isz:ex,iszw:3264,iszh:2448&tbm=isch';
var prefix = '[' + query + ']  ';

console.log(url);

var downloads_dir = 'downloads/';
var completed_dir = 'completed/';
var urls_dir = 'urls/';
var urlMemo = {};
var watchdog = null;

// With the image size constrained, this gives us photos that match the iPhone 5 sensor resolution.
casper.start(url);
casper.userAgent('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.13+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2');

casper.wait(1000, function() {
    console.log('Trying to open first image');
    casper.page.sendEvent('keypress', casper.page.event.key.Right);
    casper.page.sendEvent('keypress', casper.page.event.key.Enter);
})

function choice(list) {
    return list[Math.floor(Math.random() * list.length)];
}

function nextImage() {
    casper.page.sendEvent('keypress', casper.page.event.key.Right);
    casper.wait(50, nextImage);
}
nextImage();

function toFilename(dir, url) {
    return dir + encodeURIComponent(url) + '.jpeg';
}

function resetWatchdog() {
    // If we stop discovering anything new, end the process
    if (watchdog) {
        clearTimeout(watchdog);
    }
    watchdog = setTimeout(function() {
        console.log('Watchdog exit.');
        phantom.exit();
    }, 10000);
}

function discoveredImage(url) {
    if (urlMemo[url]) {
        // Already seen it
        return;
    }

    // Don't visit the same URL twice
    urlMemo[url] = true;

    var downloadFile = toFilename(downloads_dir, url);
    var completedFile = toFilename(completed_dir, url);
    var urlsFile = toFilename(urls_dir, url);

    if (fs.exists(downloadFile) || fs.exists(completedFile) || fs.exists(urlsFile)) {
        console.log(prefix + 'Already have ' + url);
    } else {
        // Remember to download this later by touching a file in the 'urls' directory
        console.log(prefix + 'Logging ' + url);
        fs.touch(urlsFile);
        resetWatchdog();
    }
}

casper.on('resource.received', function(response) {
    //console.log('Receive URL ' + response.url + ' status=' + response.status + ' stage=' + response.stage);

    /*
     * Only save images that didn't come from google directly.
     */

    if (response.contentType == 'image/jpeg' &&
        response.status == 200 &&
        response.url &&
        response.url.indexOf('http') == 0 &&
        response.url.indexOf('https://www.google.com/') != 0 &&
        response.url.indexOf('gstatic.com/') < 0) {

        discoveredImage(response.url);
    }

    /*
     * Also look at these 'imgrc' URLs, which leak the full URL of the resource.
     */

    if (response.url.indexOf('https://www.google.com/imgrc?') == 0) {
        var url = decodeURIComponent(response.url.split('&imgurl=')[1].split('&')[0]);
        //console.log('imgrc ' + url);
        discoveredImage(url);
    }
});

resetWatchdog();
casper.run();
