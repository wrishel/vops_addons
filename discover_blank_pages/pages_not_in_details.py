
'''Create a list of images that may need to be hand-processed.

Inputs are:

    all the file names of images in directories below IMAGE_SOURCE

    all the file names from details_fuzzy.csv from DETAILS_IMAGES
        (created at the command line)

Outputs are:

    REPORT, all the file names in IMAGE_SOURCE that were not processed by VOPS,
        including files that are only blank backside of ballots.

'''

# set of all pages in images directory

# set of all files named in details

# print difference

def ftime(atime):
    return time.strftime('%H:%M:%S', atime)

import os
import time
from DetailLine.DetailLine import *

SHORTRUN = None
PROGRESS = 1000
MAXFILE = '299999'
FILE_NAME_SUFFIX = '26'
IMAGE_SOURCE = '/Users/Wes/NotForTheCloud/2018_Nov/unproc'
pth_big_files = '/Users/Wes/NotForTheCloud/2018_Nov/in-process'
DETAILS_IMAGES = os.path.join(pth_big_files, 'details_fuzzy_sorted' + FILE_NAME_SUFFIX + '.csv')
REPORT = '/Users/Wes/Dropbox/Programming/ElectionTransparency/vops_addons/output/files_not_in_details' \
    + FILE_NAME_SUFFIX + '.csv'
PROCESS_ONLY = [
    # '231498.jpg'
]
print 'START TIME: {}'.format(ftime(time.localtime()))

files_in_dir = set()
files_in_details = set()

outcnt = 0

# create a set of images in the scanned images directories
#
for dirpath, dirnames, filenames in os.walk(IMAGE_SOURCE):
    for filename in filenames:
        if '.jpg' != filename[-4:].lower() or filename > MAXFILE:
            continue

        if len(PROCESS_ONLY) == 0 or filename in PROCESS_ONLY:
            files_in_dir.add(filename)
print "DIRECTORY SCAN COMPLETE: {}".format(ftime(time.localtime()))
with open(DETAILS_IMAGES) as inf:
    for x in inf:
        dl = Detail_line(x)
        if len(PROCESS_ONLY) == 0 or dl.file in PROCESS_ONLY:
            files_in_details.add(dl.file)

diff = files_in_dir - files_in_details
print len(diff)
with open(REPORT, 'w') as ouf:
    for x in sorted(diff):
        ouf.write('{}\n'.format(x))
