
"""Given a list of pct-ds, details_fuzzy.csv to identify the relevant image files
   and copy them to a zip file"""

import shutil
from DetailLine.DetailLine import *

class Params(object):   # https://stackoverflow.com/questions/1325673/how-to-add-property-to-a-class-dynamically/1333275
    pass

params = Params()

# Set parameters for the run
#
params.DETAILS = '/Users/Wes/Dropbox/Programming/ElectionTransparency/vops_addons/output/details_fuzzy.csv'
params.IMAGES_OUT_DIR = '/Users/Wes/Downloads/images_for_KC/'
params.IMAGES_IN_DIR = '/Users/Wes/NotForTheCloud/2018_Nov/unproc/'
params.IMAGE_LIST = '/Users/Wes/Downloads/image_list'



# copy files based on list in the file params.IMAGE_LIST
#
with open(params.IMAGE_LIST) as inf:
    for line in inf:
        fname = line.strip()
        fpath = params.IMAGES_IN_DIR + fname[0:3] + '/' + fname
        shutil.copy2(fpath, params.IMAGES_OUT_DIR)
