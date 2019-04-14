"""Accept a list of images that are missing from Details.py and create a list of the images that
   are not empty back pages.

   The missing image file, MISSING_IMAGES, can be created by pages_not_in_details.py.

   The output, REPORT, is a list of files that must be hand-procssed to supplement VOPS.
"""

import numpy
from PIL import Image
import os
import time



SHORTRUN = None
PROGRESS = 500
EMPTY_THRESHOLD = 251.5     # Luminance > this => blank page
FILE_NAME_SUFFIX = '26'

REPORT = '../output/images_to_hand_processNN.tsv'   # Images that are probably blank back pages
REPORT = REPORT.replace('NN', FILE_NAME_SUFFIX)
MAXFILE = '299999'
IMAGE_SOURCE = '/Users/Wes/NotForTheCloud/2018_Nov/unproc'

# input list of images not present in details.csv
#
MISSING_IMAGES = \
    '/Users/Wes/Dropbox/Programming/ElectionTransparency/vops_addons/output/files_not_in_detailsNN.csv'
MISSING_IMAGES = MISSING_IMAGES.replace('NN', FILE_NAME_SUFFIX)
start_time = time.localtime()
start_times = time.strftime('%H:%M:%S', start_time)
print 'START TIME: {}'.format(start_times)

def mean_lum(item):
    '''Compute the mean luminescence of a portion of a color image,
       converting it to grayscale using Pillow's formula.
    '''
    imname = item[-10:]
    try:
        im = Image.open(item).convert('L')
        empty_area = (300, 150, 2310, 2001)
        region = im.crop(empty_area)
        nmpimg = numpy.asarray(region)
    except Exception(item) as e:
        print Exception.__repr__()
        return None
    return (nmpimg.mean())


# ------------------------------------------------ MAIN

img_list = []
incnt = 0
with open(MISSING_IMAGES) as inf:
    for line in inf.read().split():
        img_list.append(line)
        incnt += 1
        if SHORTRUN and incnt > SHORTRUN:
            break

print 'TOTAL IMAGES TO PROCESS: ' + str(len(img_list))
start_list_time = time.localtime()
incnt = 0
outcnt = 0

with open(REPORT, 'w') as outf:
    for filename in sorted(img_list):
        lum = mean_lum(os.path.join(IMAGE_SOURCE, filename[:3], filename))
        if lum < EMPTY_THRESHOLD:
            outf.write('{}\t{}\n'.format(filename, str(lum)))
            outf.flush()
            outcnt += 1

        incnt += 1
        if incnt % PROGRESS == 0:
                files_pct = 100.0 * incnt / len(img_list)
                cur_time = time.localtime()
                # elapsed_time = cur_time - start_list_time

                print '{} {:8,d} {:12} {:5.1f} {:6.2f}% {:6,d}'.format(time.strftime('%H:%M:%S'),
                    incnt, filename, lum, files_pct, outcnt )
