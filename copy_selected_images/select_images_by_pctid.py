
"""Given a list of pct-ds, details_fuzzy.csv to identify the relevant image files
   and copy them to a zip file"""

import shutil
from DetailLine.DetailLine import *

class Params(object):   # https://stackoverflow.com/questions/1325673/how-to-add-property-to-a-class-dynamically/1333275
    pass

params = Params()

# Set parameters for the run
#
params.PCTIDS = ['5T--1']
params.DETAILS = '/Users/Wes/Dropbox/Programming/ElectionTransparency/vops_addons/output/details_fuzzy.csv'
params.IMAGES_OUT_DIR = '/Users/Wes/Dropbox/Programming/ElectionTransparency/vops_addons/output/images/'
params.IMAGES_IN_DIR = '/Users/Wes/NotForTheCloud/2018_Nov/unproc/'

with open(params.DETAILS) as inf:
    for line in inf:
        dl = Detail_line(line)
        if dl.pctid in params.PCTIDS:
            inpath = '{}{}/{}'.format(params.IMAGES_IN_DIR, dl.file[:3], dl.file)
            print inpath
            shutil.copy2(inpath, params.IMAGES_OUT_DIR)
