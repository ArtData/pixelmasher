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

def scaleImageDctMinMax(s):
    # Try to cut down JPEG compression artifacts by using a separate min/max
    # for each channel and for each index within the 8x8 DCT block.
    # Note: This doesn't actually work as expected, not using this for now.

    # Reshape the array to add extra axes for block index and position within block
    dct_size = 8
    dct_shape = (s.shape[0] / dct_size, dct_size, s.shape[1] / dct_size, dct_size, 3)
    dcts = s.reshape(dct_shape)

    # Collapse the block index axes via min/max functions
    block_min = numpy.min(numpy.min(dcts, axis=0), axis=1)
    block_max = numpy.max(numpy.max(dcts, axis=0), axis=1)
    assert block_min.shape == (dct_size, dct_size, 3)
    assert block_max.shape == (dct_size, dct_size, 3)

    # Tile these images back to the size of the whole image
    tiled_min = numpy.tile(block_min, (s.shape[0] / dct_size, s.shape[1] / dct_size, 1))
    tiled_max = numpy.tile(block_max, (s.shape[0] / dct_size, s.shape[1] / dct_size, 1))

    return (s - tiled_min).astype(float) / (tiled_max - tiled_min)

def gaussianBlur(s, sigma):
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


print "Loading sum buffer"
s = numpy.load('sum.npy')

print "Scaling values"

# Most raw: just scale by the max
saveTiff('result-single-max.tiff', scaleImageSingleMax(s))

# Next, show both min and max scaling
saveTiff('result-single-minmax.tiff', scaleImageSingleMinMax(s))

# Now scale each channel separately
scaled = scaleImageChannelMinMax(s)
saveTiff('result-channel-minmax.tiff', scaled)

# Gaussian filter, to extract only the low-frequency color gradient background
print "Blurring"
lowpass = gaussianBlur(scaled, int(s.shape[1] * 0.05))
saveTiff('result-lowpass.tiff', lowpass)

# Subtract the blurred image, for a high-pass filter
highpass = scaled - lowpass
saveTiff('result-highpass.tiff', gammaCorrect(scaleImageCenterMinMax(highpass), 2.2))

# Emphasize differences by squaring the error
sq = highpass * highpass
saveTiff('result-highpass-sq.tiff', gammaCorrect(scaleImageCenterMinMax(sq), 1/2.2))
