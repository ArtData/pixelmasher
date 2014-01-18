/*
 * Batch downloader.
 *
 * Looks for placeholder files in the 'urls' directory,
 * downloads them, and places the results in 'downloads' or 'failed'.
 *
 * npm install queue-async httpreq
 *
 * Micah Elizabeth Scott <micah@scanlime.org>
 */

var fs = require('fs');
var httpreq = require('httpreq');
var queue = require('queue-async');

// Highly concurrent!
var q = queue(32);

//+ Jonas Raoni Soares Silva
//@ http://jsfromhell.com/array/shuffle [v1.0]
function shuffle(o){ //v1.0
    for(var j, x, i = o.length; i; j = Math.floor(Math.random() * i), x = o[--i], o[i] = o[j], o[j] = x);
    return o;
};

function look_for_work() {
    // Shuffle files so we hit lots of different servers
    var filenames = shuffle(fs.readdirSync('urls'));

    for (var i = 0; i < filenames.length; i++) {
        var filename = filenames[i];
        if (filename.slice(-5) == '.jpeg') {
            var url = decodeURIComponent(filename.slice(0, -5));
            enqueue_download(filename, url);
        }
    }

    q.awaitAll( function(error, results) {  
        console.log("Done with batch");
        process.exit(0);
    })
}

function enqueue_download(filename, url) {
    q.defer( function(callback) {
        console.log('Begin ' + url);

        httpreq.get(url, {binary: true}, function(error, res) {
            if (error) {
                console.log('Error fetching ' + url + ': ' + error);
            } else {
                fs.writeFileSync('downloads/' + filename, res.body);
                fs.unlinkSync('urls/' + filename);
                console.log('Complete ' + url);
            }
            callback();
        });
    })
}

look_for_work();
