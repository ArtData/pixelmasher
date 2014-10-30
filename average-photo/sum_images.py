#!/usr/bin/env python
#
# Sort through the downloaded images. If they're good,
# sum them into a big buffer and save that buffer to a numpy data file.
#

import os, numpy, Image, multiprocessing

input_dir = 'downloads'
failed_dir = 'failed'
completed_dir = 'completed'
output_file = 'sum.npy'

# Process concurrently in small batches and checkpoint periodically.
# Batches should be fairly large to amortize the cost of checkpointing
# the sum buffer.

num_cpus = multiprocessing.cpu_count()
batch_size_per_cpu = 400

square_size = 1024


def newBuffer():
    return numpy.zeros((square_size, square_size, 3), dtype=numpy.uint64)

def loadBuffer():
    # Load old buffer or create a zeroed buffer
    if os.path.exists(output_file):
        print "Loading buffer"
        return numpy.load(output_file)
    else:
        print "Creating new buffer"
        return newBuffer()

def saveBuffer(buffer):
    print "Writing results"
    numpy.save(output_file, buffer)

def makeLUT():
    # Make a lookup table for converting sRGB to linear RGB in 16-bit precision.
    # This does our whole mapping in one step, including conversion to uint64 type :)
    return (pow(numpy.arange(256) / 255.0, 2.2) * 0xFFFF).astype(numpy.uint64)

def prepareBatches():
    # Divide up images into per-CPU batches
    batches = [[] for i in range(num_cpus)]
    count = 0

    for f in os.listdir(input_dir):
        if f.startswith('.'):
            continue
        batch = batches[count % num_cpus]
        batch.append(f)
        count += 1
        if count >= batch_size_per_cpu * num_cpus:
            break

    print "Starting batch of %d images on %d CPUs" % (count, num_cpus)
    return batches, count

def moveCompletedFiles(fileList):
    print "Moving completed files"

    # Now move every file we've processed
    for filename in fileList:
        os.rename(os.path.join(input_dir, filename), os.path.join(completed_dir, filename))

def moveFailedFile(filename):
    os.rename(os.path.join(input_dir, filename), os.path.join(failed_dir, filename))

def worker(batch):    
    file_list = []
    buf = newBuffer()
    lut = makeLUT()

    for filename in batch:
        print filename

        try:
            img = Image.open(os.path.join(input_dir, filename))

            if img.mode != 'RGB':
                # Convert incurs an extra copy, only do this if the image isn't already RGB.
                img = img.convert('RGB')

            # Resize so it fits in the sum buffer
            ratio = float(square_size) / max(img.size[0], img.size[1])
            scaled_width = int(img.size[0] * ratio)
            scaled_height = int(img.size[1] * ratio)
            x_offset = int((square_size - scaled_width) / 2)
            y_offset = int((square_size - scaled_height) / 2)

            img = img.resize((scaled_width, scaled_height), Image.ANTIALIAS)

            # Copy to a numpy array
            f = numpy.fromstring(img.tostring(), numpy.uint8).reshape(scaled_height, scaled_width, 3)

        except (IOError, IndexError, SyntaxError), e:
            # Failed to read this image, immediately move it out of the way
            print "  failed (%r)" % e
            moveFailedFile(filename)
            continue

        buf[y_offset:(y_offset+scaled_height), x_offset:(x_offset+scaled_width), :] += lut[f]
        file_list.append(filename)

    return buf, file_list


def main():
    sum_buffer = loadBuffer()
    p = multiprocessing.Pool(num_cpus)

    while True:
        print "Loading image list"

        batches, count = prepareBatches()
        if not count:
            break

        # Submit each batch as a separate task
        results = p.map(worker, batches, 1)

        print "Accumulating results"
        summed_files = []
        for buf, file_list in results:
            sum_buffer += buf
            summed_files.extend(file_list)

        moveCompletedFiles(summed_files)
        saveBuffer(sum_buffer)

    p.close()
    print "Done"


if __name__ == '__main__':
    main()

