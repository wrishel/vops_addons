
"""Print to the console the mean value of the luminance of Grayscale versions of ballot images,
selecting the pixels from the top part of the page which excludes the borders and
merging and extends down not quite to the "This page left blank"
notation. See the definition of empty_area below for the exact box.

In a sample of 1% of ~ 220000, 8-1/2 x 14, 300-dpi images, the mean values of

    > 254.0 had empty ballot pages.

    253-249 were page-4s with actual voteops on them

    233 was a legit ballot page upside down

    <= 231 legitimate ballots


"""

import numpy
from PIL import Image
import os
import random

SHORTRUN = None
PROGRESS = 10000
SAMPLE = .02
outcnt = 0

base = '/Users/Wes/NotForTheCloud/2018_Nov/unproc'
imglist = {}  # (filename, meanbrightness)

def measure1(item, imglst):
    if random.random() > SAMPLE:
        return
    imname = item[-10:]
    im = Image.open(item).convert('L')
    empty_area = (300, 150, 2310, 2001)
    region = im.crop(empty_area)
    nmpimg = numpy.asarray(region)
    roundedmean = round(nmpimg.mean(), 2)
    piclist = imglist.get(roundedmean, [])
    piclist.append(imname)
    imglist[roundedmean] = piclist

#  ------------------------------------------------------  MAIN
#
for dirpath, dirnames, filenames in os.walk(base):
    if SHORTRUN and outcnt > SHORTRUN:
        break
    for filename in filenames:
        if '.jpg' == filename[-4:].lower():
            measure1(os.path.join(dirpath, filename), imglist)
        outcnt += 1
        if outcnt % PROGRESS == 0:
            print outcnt, filename
        if SHORTRUN and outcnt > SHORTRUN:
            break

for roundedmean in list(sorted(imglist.keys())):
    print roundedmean, len(imglist[roundedmean])
    files = imglist[roundedmean]
    continue
    for i in range(0, len(files), 5):
        j = i + 5
        if j > len(files):
            j = len(files)

        s = '\t'.join(files[i:j])
        print '\t\t' + s





