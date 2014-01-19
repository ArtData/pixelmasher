#!/usr/bin/env python
#
# Convert the 64-bit sum buffer into a 16-bit tiff, by scaling
# the min/max values in the buffer to the range of the output file.
#
# We generate two outputs, one per-channel (false color) and one
# true-color (global max/min).
#

import os
import numpy
import tifffile
import scipy.ndimage.filters

def scaleImage(s, min_value, max_value):
    print "Value range [%s, %s]" % (min_value, max_value)
    return (s - min_value).astype(float) / (max_value - min_value)

def scaleImageSingleMax(s):
    return scaleImage(s, 0, numpy.max(s))

def scaleImageSingleMinMax(s):
    return scaleImage(s, numpy.min(s), numpy.max(s))

def scaleImageChannelMinMax(s):
    return scaleImage(s,
        numpy.min(s.reshape(-1, 3), axis=0),
        numpy.max(s.reshape(-1, 3), axis=0))

def scaleImageCenterMinMax(s):
    # Like scaleImageChannelMinMax(), but we only look at the min/max values within
    # the middle 2/3 of the image, ignoring the edges. This allows the edges to oversaturate,
    # but it lets us see much more detail in the center.

    dim = (s.shape[0] * 2//3, s.shape[1] * 2//3)
    margin = ((s.shape[0] - dim[0]) // 2, (s.shape[1] - dim[1]) // 2)
    center = s[ margin[0]:margin[0]+dim[0], margin[1]:margin[1]+dim[1], : ]

    return scaleImage(s,
        numpy.min(center.reshape(-1, 3), axis=0),
        numpy.max(center.reshape(-1, 3), axis=0))

def vRatio(a, b):
    # Ratio of two vector magnitudes
    return numpy.max(numpy.abs(a) / numpy.abs(b))

def removeDctBlockArtifacts(s):
    # The raw sum buffer ends up with a very noticeable repeating 8x8 pattern due to
    # systemic errors in the JPEG compression process. We try to cancel these out by
    # removing those components in the frequency domain.

    print "Removing DCT block artifacts"
    f = numpy.fft.rfft2(s, axes=(0,1))
    saveTiff('result-dct-spectrum-before.tiff', scaleImageChannelMinMax(numpy.log(numpy.abs(f) + 1)))

    # Keep a queue of FFT hotspots to examine
    queue = []

    # Energy ratio threshold for an FFT hotspot
    threshold = 0.5

    # FFT energy for random tiled 8x8 data appears in this grid pattern

    for i in range(0, f.shape[0]+1, s.shape[0]/8):
        for j in range(0, f.shape[1]+1, s.shape[1]/8):

            # The last row is just off the edge of the image; nudge it back in.
            i = min(i, f.shape[0] - 1)
            j = min(j, f.shape[1] - 1)

            # Don't zero the DC component
            if i == 0 and j == 0:
                continue

            # The energy from the DCT errors spreads outward from this point a little, in a
            # star-like pattern. Do a flood-fill starting from this point and moving outward.
            queue.append((i, j))

    # Erode hotspots until the queue is empty, using a flood-fill algorithm.

    memo = {}

    while queue:
        i, j = point = queue.pop()
        memo[point] = True

        # Zero this point
        x = numpy.copy(f[i, j])
        f[i, j] = 0

        # Don't bother examining neigbors for points on the DC axes
        if i == 0 or j == 0:
            continue

        # Examine neighbors
        for i, j in ( (i-1, j),
                      (i+1, j),
                      (i, j-1),
                      (i, j+1) ):
            point = i, j

            if point in memo:
                # Already seen
                continue

            if i < 0 or i >= f.shape[0] or j < 0 or j >= f.shape[1]:
                # Out of range
                continue

            # How different is this neighbor?
            if vRatio(f[i, j], x) > threshold:
                # Different enough we can stop
                continue

            # Remember to visit this neighbor
            queue.append(point)

    saveTiff('result-dct-spectrum-after.tiff', scaleImageChannelMinMax(numpy.log(numpy.abs(f) + 1)))
    return numpy.fft.irfft2(f, axes=(0,1))

def gaussianBlur(s, sigma=None):
    print "Blurring"
    sigma = sigma or s.shape[1] * 0.05
    return numpy.dstack((
        scipy.ndimage.filters.gaussian_filter(s[:,:,0], sigma),
        scipy.ndimage.filters.gaussian_filter(s[:,:,1], sigma),
        scipy.ndimage.filters.gaussian_filter(s[:,:,2], sigma)))

def gammaCorrect(s, exp):
    return pow(numpy.clip(s, 0, 1), exp)

def saveTiff(filename, s):
    # Convert floating point to 16-bit TIFF
    print 'Writing %s' % filename
    s = s * float(0xFFFF)
    numpy.clip(s, 0, 0xFFFF)    
    tifffile.imsave(filename, s.astype(numpy.uint16))

def scaleAndFilterImage(s, prefix):
    # Most raw: just scale by the max
    saveTiff(prefix + 'single-max.tiff', scaleImageSingleMax(s))

    # Next, show both min and max scaling
    saveTiff(prefix + 'single-minmax.tiff', scaleImageSingleMinMax(s))

    # Now scale each channel separately
    scaled = scaleImageChannelMinMax(s)
    saveTiff(prefix + 'channel-minmax.tiff', scaled)

    # Gaussian filter, to extract only the low-frequency color gradient background
    lowpass = gaussianBlur(scaled)
    saveTiff(prefix + 'lowpass.tiff', lowpass)

    # Subtract the blurred image, for a high-pass filter
    highpass = scaled - lowpass
    saveTiff(prefix + 'highpass.tiff', gammaCorrect(scaleImageCenterMinMax(highpass), 2.2))

    # Emphasize differences by squaring the error
    sq = highpass * highpass
    saveTiff(prefix + 'highpass-sq.tiff', gammaCorrect(scaleImageCenterMinMax(sq), 1/2.2))


def main():
    print "Loading sum buffer"
    s = numpy.load('sum.npy')

    # First round of filtering
    scaleAndFilterImage(s, 'result-')

    # Do it all again after trying to remove DCT block artifacts
    dcts = removeDctBlockArtifacts(s)
    scaleAndFilterImage(dcts, 'result-dct-')


if __name__ == '__main__':
    main()

