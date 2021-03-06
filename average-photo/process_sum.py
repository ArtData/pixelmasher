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
    # the middle 1/5 of the image, ignoring the edges. This allows the edges to oversaturate,
    # but it lets us see much more detail in the center.

    dim = (s.shape[0]//5, s.shape[1]//5)
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

    # FFT energy for random tiled 8x8 data appears in this grid pattern
    for i in range(0, f.shape[0], s.shape[0]/8):
        for j in range(0, f.shape[1], s.shape[1]/8):
            if i == 0 and j == 0:
                # Skip the DC component
                continue
            f[i, j] = 0

    saveTiff('result-dct-spectrum-after.tiff', scaleImageChannelMinMax(numpy.log(numpy.abs(f) + 1)))
    return numpy.fft.irfft2(f, axes=(0,1))

def gaussianBlur(s, sigma=None):
    print "Blurring"
    sigma = sigma or s.shape[1] * 0.03
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


if __name__ == '__main__':
    main()

