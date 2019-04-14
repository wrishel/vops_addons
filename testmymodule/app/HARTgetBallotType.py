""" Obtain the ballot type ID from a HART ballot by bar-code or, optical recognition.

    This code was written for the Humboldt Election Transparency Project and is licensed
    but under the MIT License and the Beer License.
"""

import tesseract
from PIL import Image
from PIL import ImageFile  # fix for IOError('image file is truncated ...
ImageFile.LOAD_TRUNCATED_IMAGES = True
from pyzbar.pyzbar import decode, ZBarSymbol
import codecs
import os
import re
import sys
import time
from string import digits
# import logging        # logging commented out, should be used by caller if wanted

global bc_count, bc_proctime, ocr_count, ocr_proctime
bc_count, bc_proctime, ocr_count, ocr_proctime = 0, 0.0, 0, 0.0

class HARTgetBallotType:

    def __init__(self):

        self.DPI = 300  # scanning resolutions lower than use impact recognition
        inchToPx = lambda x: int(float(x) * self.DPI + .5)

        # HART Ballot Locations
        #
        # Printed number runs vertically in left margin. These crops
        # allow for misalignment but aren't too generous because the OCR
        # algorithm is sensitive to dirt on the page.
        #
        self.OCR_TOP_LEFT_X_PX = inchToPx(0.075)
        self.OCR_TOP_LEFT_Y_PX = inchToPx(3.1)
        self.OCR_BOT_RIGHT_X_PX = inchToPx(0.53)
        self.OCR_BOT_RIGHT_Y_PX = inchToPx(5.0)
        self.OCR_DELTA_X_PX = inchToPx(0.1)
        self.OCR_DELTA_Y_PX = inchToPx(0.1)

        # Barcode also runs vertically in the left margin. the crops are generously
        # wide, which works OK with pyzbar.
        #
        self.BARCODE_TOP_LEFT_X_PX = inchToPx(0.09)
        self.BARCODE_TOP_LEFT_Y_PX = inchToPx(0.45)
        self.BARCODE_BOT_RIGHT_X_PX = inchToPx(0.87)
        self.BARCODE_BOT_RIGHT_Y_PX = inchToPx(3.3)  # wjr 9/25/18

        self.goodnum = re.compile(r'^\d{14}$')  # The only acceptable format.
        self.successfulMode = None

    def getBallotType(self, file):
        """
        :param fd: file:
        :return string: Ballot type string of digits or None
        """
        global bc_count, bc_proctime, ocr_count, ocr_proctime
        self.upsideDownImage = None
        self.successfulMode = None
        # logging.info(file)
        image = Image.open(file)
        image.load()                # for time testing

        start = time.time()
        barcode = self._scanBarcode(image)
        # logging.info(barcode)
        if barcode:
            bc_count += 1
            bc_proctime += time.time() - start
            return barcode

        # Barcode didn't work; try OCR-ing the ballot.
        return self._ocrBallotID(image)

    # In order to assure that tesseract gets closed, this class is
    # instantiated through __enter__ for use with the With statement.
    #
    def __enter__(self):
        # self.tessAPI = PyTessBaseAPI()  # Tesseract API
        # self.tessAPI.SetVariable('tessedit_char_whitelist', digits)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # self.tessAPI.End()
        return False        # if terminated by exception raise it now

    def _ocrBallotID(self, image, deltaX=0, deltaY=0, upsideDown=False):
        """OCR the number that indicates the ballot format
           and contains the key to the precinct.

        :param Image image:  a Pillow image of the full scanned ballot side.
        :param int deltaX: a cushion around the target number when scanning upside down.
        :param int deltaY: a cushion around the target number when scanning upside down.
        :return string: the OCR'pct_tots digits or None

        """

        # The error rate could probably be improved here by thresholding all
        # pixels of the cropped image with substantial color (i.e., not white or
        # black) to white. Performance penalty would be small
        # because most pages are handled with bar codes.
        #
        if upsideDown:
            if not self.upsideDownImage:
                self.upsideDownImage = image.transpose(Image.ROTATE_180)
            cropped = self.upsideDownImage.crop(
                (self.OCR_TOP_LEFT_X_PX - self.OCR_DELTA_X_PX,
                 self.OCR_TOP_LEFT_Y_PX,
                 self.OCR_BOT_RIGHT_X_PX,
                 self.OCR_BOT_RIGHT_Y_PX + self.OCR_DELTA_Y_PX)).transpose(Image.ROTATE_270)

        else:
            cropped = image.crop((self.OCR_TOP_LEFT_X_PX,
                                  self.OCR_TOP_LEFT_Y_PX,
                                  self.OCR_BOT_RIGHT_X_PX,
                                  self.OCR_BOT_RIGHT_Y_PX)).transpose(Image.ROTATE_270)

        self.tessAPI.SetImage(cropped)
        txt = tesserocr.image_to_text(image)
        # logging.info(txt)

        # Ignore embedded spaces in OCR'pct_tots text. Even thought we specify only digits Tesseract
        # may embed spaces in the text.
        #
        txt = txt.replace(' ', '')
        # logging.info(txt)
        if self.goodnum.match(txt):
            self.successfulMode = 'o'
            # logging.info(txt)
            return txt
        if upsideDown:
            logging.info('try upside down')
            return None  # already tried upside down, so give up
        return self._ocrBallotID(image, deltaX, deltaY, True)  # try upside down

    def _scanBarcode(self, image, upsideDown=False):
        """Capture the ballot ID from the barcode.

        :param Image image:  a Pillow image of the full scanned ballot side.
        :param Boolean upsideDown:  a Pillow image of the full scanned ballot side.
        :return string: the bar code digits or None
        """
        img = image
        if upsideDown:
            if not self.upsideDownImage:
                self.upsideDownImage = image.transpose(Image.ROTATE_180)
                img = self.upsideDownImage

        bcimage = img.crop((self.BARCODE_TOP_LEFT_X_PX,
                            self.BARCODE_TOP_LEFT_Y_PX,
                            self.BARCODE_BOT_RIGHT_X_PX,
                            self.BARCODE_BOT_RIGHT_Y_PX))
        x = 0
        if x:
            bcimage.show()
        barcodes = decode(bcimage, symbols=[ZBarSymbol.I25])

        # Pyzbar can return some ghost barcodes. (This may be fixed now).
        #
        for i in reversed(range(len(barcodes))):
            bcd = barcodes[i]
            if bcd.rect.width == 0 or not self.goodnum.match(bcd.data):
                del barcodes[i]

        if len(barcodes) == 1:
            self.successfulMode = 'b'
            return barcodes[0].data
        if upsideDown:
            return None  # we already tried upside down so punt.
        return self._scanBarcode(image, True)

#
#  -----------------------------------------  MAIN  -----------------------------------------
#

# Imports used solely for testing.


if __name__== '__main__':
    import json
    import fnmatch

    # source of test images
    #
    testingPath = os.path.join( globcon.PROJ_PATH, 'testing','HARTgetBallotTypeTest')
    images = testingPath
    readwrite = 'r'  # r to read values expected during testing. 'w' to rewrite those values.
    dataoutf = '/Users/Wes/Dropbox/Programming/Python/etpruncnt2.1/data/testout.txt'

    images = '/Users/Wes/NotForTheCloud/2017_Nov/imgByPct'
    images = '/Users/Wes/NotForTheCloud/2018_June/unproc'
    HIGHEST_IMAGE_FILE = '128241.jpg''104308.jpg'

    onlyTheseForTesting = []

    tstart = time.time()
    d = {}
    cnt = 0
    bcd = 0
    ocr = 0
    lastdir = None
    quitAfter = None

    with HARTgetBallotType() as hgbt:
        for root, dirs, files in os.walk(images):
            for f in files:

                # Construct output for testing
                #
                if fnmatch.fnmatch(f, '*.jpg') and f <= HIGHEST_IMAGE_FILE:
                    if not onlyTheseForTesting or f in onlyTheseForTesting:

                        cnt += 1
                        pth = os.path.join(root, f)
                        try:
                            ballotID = hgbt.getBallotType(pth)
                        except Exception as e:
                            sys.stderr.write("Exception on file '{}'\n{}\n".format(f, repr(e)))
                            continue

                        if hgbt.successfulMode == 'b':
                            x = '{} (bc)'.format(ballotID)
                            bcd += 1
                        elif hgbt.successfulMode == 'o':
                            x = '{} (ocr)'.format(ballotID)
                            ocr += 1
                        else:
                            x = '(no bc or ocr)'
                            print cnt, root, f
                        relpath = codecs.encode(os.path.relpath(pth, images))  # Unicode to ASCII
                        x = codecs.encode(x)  # Unicode to ASCII
                        if x in d:
                            d[x].append(relpath)
                        else:
                            d[x] = [relpath]
                        if (cnt % 100) == 0:
                            telapse = time.time() - tstart
                            print 'n={:>6,}; et={:>6.1f}; avg={:>6.6f}; bcd={}; ocr={}'\
                                .format(cnt, telapse, bc_proctime / bc_count, bcd, ocr)

                        if root != lastdir:
                            print root
                            lastdir = root

                        if cnt == quitAfter: break

    telapse = time.time() - tstart
    print telapse, telapse / cnt
    with open(dataoutf, 'w') as ouf:
        for k in sorted(d.keys()):
            l = len(d[k])
            s = str(d[k][:3])
            if l > 3: s += ' ...'
            ouf.write('{} {} {}\n'.format(k, l, s))

    if images == testingPath:
        testvals = []
        for k in sorted(d.keys()):
            testvals.append([k, sorted(d[k])])   # values in UTF-8

        p = os.path.join(testingPath, 'outfile.json')
        if readwrite == 'r':
            with open(p, 'r') as inf:
                dtest = json.load(inf)  # values in Unicode


            assert testvals == dtest
        else:
            with open(os.path.join(testingPath, 'outfile.json'), 'w') as of:
                json.dump(testvals, of)
