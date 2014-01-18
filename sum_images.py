#!/usr/bin/env python
#
# Sort through the downloaded images. If they're good,
# sum them into a big buffer and save that buffer to a numpy data file.
#

import os, numpy, Image

input_dir = 'downloads'
failed_dir = 'failed'
completed_dir = 'completed'
output_file = 'sum.npy'
batch_size = 50

# Load old buffer or create a zeroed buffer
if os.path.exists(output_file):
    sum_buffer = numpy.load(output_file)
else:
    sum_buffer = numpy.zeros((2448, 3264, 3), dtype=numpy.uint64)

# Make a lookup table for converting sRGB to linear RGB in 16-bit precision.
# This does our whole mapping in one step, including conversion to uint64 type :)
lut = (pow(numpy.arange(256) / 255.0, 2.2) * 0xFFFF).astype(numpy.uint64)


# Process in small batches and checkpoint periodically
while True:
    print "Loading image list"
    batch = [f for f in os.listdir(input_dir)[:batch_size] if f.endswith('.jpeg')]
    
    if not batch:
        break

    # Keep track of images we've processed this time
    summed_files = []

    for filename in batch:
        print filename

        try:
            img = Image.open(os.path.join(input_dir, filename)).convert('RGB')
            f = numpy.fromstring(img.tostring(), numpy.uint8).reshape(img.size[1], img.size[0], 3)

        except (IOError, IndexError, SyntaxError), e:
            # Failed to read this image, immediately move it out of the way
            print "  failed (%r)" % e
            os.rename(os.path.join(input_dir, filename), os.path.join(failed_dir, filename))
            continue

        if f.shape != sum_buffer.shape:
            print "  wrong size"
            os.rename(os.path.join(input_dir, filename), os.path.join(failed_dir, filename))
            continue

        # Add it to our sum buffer, and remember to move it after we write out the results
        sum_buffer += lut[f]
        summed_files.append(filename)

    print "Writing results"

    # Write out the results!
    numpy.save(output_file, sum_buffer)

    print "Moving completed files"

    # Now move every file we've processed
    for filename in summed_files:
        os.rename(os.path.join(input_dir, filename), os.path.join(completed_dir, filename))

print "Done"
