import copy
import cv2
import gc
import glob
import io
import logging
import math
import numpy as np
import os
import pickle
from PIL import Image, ImageDraw, ImageFont
import pytesseract
import pdb
import pdfkit
from pyzbar import pyzbar 
import regex 
import shutil
import sqlite3
import statistics
import sys
import tarfile
import tempfile
import time
from vops_error import ReconciliationError, BarcodeError, NoImageReadFromFileError, InvalidBoxOffsetError
from vops_vop import VoteOp
import vops_image_util as viu

# Note that --psm 7 tells tesseract to use page segmentation mode 7,
# which treats text as a single line
# and --psm 6 tell tesseract to treat text as a single uniform block
def sortbyfields02(e):
    """Sort vertically within 300 pixel wide stripes (likely 1 or 2 inches)"""
    return ((e[0]/600)*18000)+e[1]

def get_contest_text(bi,bis,line_above,v,vvxo,last_contest_text):
    """Extract contest_text from specified region"""
    # vvxo abbreviation of valid vote x offsets
    dpi = bi.args.dpi
    if abs(line_above - v.y) < (dpi/6):
        return last_contest_text,None
    # Crop from region below line_above
    # and above the location 0.1" below the y offset of the vote op 
    start_text = v.x - (dpi/16)
    for vvx in vvxo:
        if abs(vvx - v.x) < (dpi/3):
           start_text = vvx - (dpi/16) 
    end_text = v.x + bi.args.column_width - bi.args.column_margin
    cropped = bi.tmp_cv2_im[line_above+(dpi/60):v.y,start_text:end_text]
    t=''
    try:
        t = pytesseract.image_to_string(cropped,config='--psm 6')
        t = viu.cleaned(t)
        
    except Exception as ee:
        logging.warning(ee)
        
    try:
        if bi.barcode not in bis.image_dict:
            bis.image_dict[bi.barcode] = []
        crop_im_small = cv2.resize(cropped,None,None,.25,.25,cv2.INTER_AREA)
        bis.image_dict[bi.barcode].append([t,crop_im_small])
    except TypeError as te:
        print te
        logging.error(te)
        t = ''
    except ValueError as ve:
        print ve
        logging.error(ve)
        t = ''
    return t[:60],cropped 

def find_y_of_contest(x,y,dpi,boxes):
    """Find y coordinate of high-width box that encloses voteop at x,y"""
    max_y = 0

    for box in boxes:
        if box[0] == 0:
            continue
        logging.info(box)
        if x > (box[0]-(dpi/2)) and x < (box[0]+box[2]):
            # box has correct horizontal offset to enclose vop
            if y > box[1]:
                # box has correct vertical offset to enclose vop
                max_y = max(box[1]+box[3],max_y)
                logging.info("Max_y %d after box %s" % (max_y,box))
    logging.info("Contest y is %d" % (max_y))
    return max_y




class BallotImage:
    """Store a ballot image with its array of vote ops."""

    def __init__(self):
        self.args = None
        self.filename = ''
        self.current_folder = ''
        self.ulc_x = -1
        self.ulc_y = -1
        self.urc_x = -1
        self.urc_y = -1
        self.tared_column_offsets = []
        self.barcode = ''
        self.precinct_text = ''
        self.hastext = 0
        self.va = []
        self.big_boxes = []
        self.writeinlines = []
        self.out_of_band = []
        self.contest_changes = []
        self.lowest_coverage = 0
        self.highest_coverage = 0
        self.reconciled = 0
        self.errors = 0
        self.rotation = 0
        self.flipped = None
        self.rotated = 0.0
        self.va_coords_from_reference = 0
        self.tmp_cv2_im = None

    def correct_reference_va(self):
        """ Fix out of bound values and re-get YES NO text if necessary."""
        # Because the reference ballot's vote array is used
        # for the coordinates of many of the ballots which
        # share its barcode, we must handle situations
        # where a user scribble outside the box
        # increases the apparent size of the box.
        dpi = self.args.dpi
        tenth = dpi/10
        allowed_height = self.args.nominal_height_of_vop + self.args.vop_slack
        allowed_width = self.args.nominal_width_of_vop + self.args.vop_slack
        # First deal with vops enlarged by scribbling
        for n in range(1,len(self.va)-1):
            try:
                # if a height exceeds nominal by more than slack,
                # check for correct starting y and adjust h
                if (self.va[n].h > allowed_height):
                    y1 = self.va[n].y
                    y2 = y1 + self.va[n].h
                    x1 = self.va[n].x
                    x2 = x1 + self.va[n].w
                    firstdark_h = viu.cv2_first_hline_with_n_dark(
                        self.tmp_cv2_im[y1:y2,x1:x2],
                        self.args.nominal_width_of_vop/2)
                    logging.info('Adjusting %s vop %d y/h by %d/%d' % (
                        self.filename,n,firstdark_h,-firstdark_h))
                    self.va[n].y += firstdark_h
                    self.va[n].h -= firstdark_h
                if (self.va[n].w > allowed_width):
                    y1 = self.va[n].y
                    y2 = y1 + self.va[n].h
                    x1 = self.va[n].x
                    x2 = x1 + self.va[n].w
                    firstdark_v = viu.cv2_first_vline_with_n_dark(
                        self.tmp_cv2_im[y1:y2,x1:x2],
                        self.args.nominal_height_of_vop/2)
                    logging.info('Adjusting %s vop %d x/w by %d/%d' % (
                        self.filename,n,firstdark_v,-firstdark_v))
                    self.va[n].x += firstdark_v
                    self.va[n].w -= firstdark_v
            except:
                logging.error(
                    'Trouble in correct_reference_va part 1, %s vop %d' % (
                        self.filename,
                        n
                    )
                )

        # then deal with any remaining offsets
        for n in range(1,len(self.va)-2):
            try:
                # if an x value is less than both the preceding
                # and following x value,
                # and the preceding and following values are within 1/10",
                # replace the x value with their average
                # before installing the vote array as the reference
                if (
                        (n+1 < len(self.va))
                         and (self.va[n].x < self.va[n-1].x)
                ):
                    if self.va[n].x < self.va[n+1].x:
                        if abs(self.va[n+1].x - self.va[n-1].x) < tenth:
                            new_x = (self.va[n-1].x + self.va[n+1].x)/2
                            self.va[n].x = new_x
                            logging.info(
                                'Updating ref va[%d], barcode %s, file %s' % (
                                    n,
                                    self.barcode,
                                    self.filename
                                )
                            )
                        if (
                                (n+2 < len(self.va))
                                and (self.va[n].x < self.va[n+2].x)
                        ):
                            if abs(self.va[n+2].x - self.va[n-1].x) < tenth:
                                new_x = (self.va[n-1].x + self.va[n+2].x)/2
                                self.va[n].x = new_x
                                msg = 'Updating ref va[%d],barcode %s,file %s' 
                                logging.info(
                                    msg % (
                                        n,
                                        self.barcode,
                                        self.filename
                                    )
                                )
                        if ( (n+3 < len(self.va))
                             and (self.va[n].x < self.va[n+3].x)
                        ):
                            if abs(self.va[n+3].x - self.va[n-1].x) < tenth:
                                new_x = (self.va[n-1].x + self.va[n+3].x)/2
                                self.va[n].x = new_x
                                msg = 'Updating ref va[%d],barcode %s,file %s'
                                logging.info(
                                    msg % (
                                        n,
                                        self.barcode,
                                        self.filename
                                    )
                                )
            except:
                logging.error(
                    'Trouble in correct_reference_va part 2, %s vop %d' % (
                        self.filename,
                        n
                    )
                )
                pass


        try:
            force_yes_no = ('PROPOS' in self.va[n].contest_text
                            or 'MEASURE' in self.va[n].contest_text) 
            no_yes_no = ('YES' not in self.va[n].choice_text
                         and 'NO' not in self.va[n].choice_text)
            nom_wid = self.args.nominal_width_of_vop
            dpi = self.args.dpi
            if force_yes_no:
                if no_yes_no:
                    logging.warning(
                        "Prop without yes or no in choice %d %s" % (
                            n,self.filename
                        )
                    )
                    x1 = self.va[n].x + nom_wid
                    x2 = x1+ (2*dpi)
                    y1 = self.va[n].y
                    y2 = y1 + self.va[n].h
                    new_text = pytesseract.image_to_string(
                        self.tmp_cv2_im[y1:y2,x1:x2],
                        config='--psm 7')
                    new_text = cleaned(new_text)
                    logging.warning(new_text)
                    if 'YES' in new_text or 'NO' in new_text:
                        self.va[n].choice_text = new_text
        except Exception as e:
            logging.error('Problem updating text to yes or no in %s vop %d' % (self.filename,n))
            print e
    
    def gen_details(self,ref):
        """Write csv lines to details.csv"""
        # Fields numbered from 1
        # 1 filename
        # 2 barcode
        # 3 contest_text
        # 4 choice_text
        # 5 initial opinion on voted,
        # 6 darkened pixel count,
        # 7-10 coords x,y,w,h (possibly after rotation),
        # 11 initial opinion on overvoted,
        # 12 mode used to collect darkened pixels
        #    1 = adjusted template coords were used,
        #    0 = conncomp blobs used because OK
        # 13 image was rotated through float degrees
        dpi = self.args.dpi
        filename = os.path.basename(self.filename)
        digits = self.barcode.replace(',',';').replace(' ','')
        with io.open('details.csv','a') as f:
            last_mx = self.va[0].x
            choice = ''
            for m in range(len(self.va)):
                if self.va[m].covered == 0:
                    print "Zero coverage, vop",m,self.filename
                    logging.error('Zero coverage, vop %d %s' % (m,self.filename))
                try:
                    if not (digits.isdigit()):
                        digits = self.barcode
                    #filename = cleaned(filename)
                    #digits = cleaned(digits)
                    contest2 = ref.va[m].contest_text
                    choice = ref.va[m].choice_text
                    voted = int(self.va[m].marked)
                    #try:
                    #    sums_dict[digits,contest2,choice] = sums_dict[digits,contest2,choice]+voted
                    #except:
                    #    sums_dict[digits,contest2,choice] = int(self.va[m].marked)
                    mx = self.va[m].x > 300
                    if mx > 300 and mx < 500:
                        if last_mx < 300:
                            print filename,m,mx
                            logging.warning("x offset 300+ %s %d %d" % (filename,m,mx))
                    last_mx = mx
                    assert len(choice)>1
                    s = '%s,%s,%s,%s,%d,%d, %d,%d,%d,%d, %d,%d,%f\n' % (
                        filename,
                        digits,
                        contest2,
                        choice,
                        self.va[m].marked,
                        self.va[m].covered,
                        self.va[m].x,
                        self.va[m].y,
                        self.va[m].w,
                        self.va[m].h,
                        self.va[m].overvoted,
                        self.va_coords_from_reference,
                        self.rotated
                    )
                    #if self.va[m].covered < 2000:
                    #    logging.error("Unacceptably low coverage %s %s %s" % (filename,contest2,choice))
                    try:
                        encoded = unicode(s)
                        f.write(encoded)
                    except UnicodeEncodeError as iuee:
                        logging.error(iuee)
                        f.write(s)
                except IndexError as ke:
                    logging.error("Unexpected Index Error %s %d %s" % (ke,m,filename))
                except KeyError as ke:
                    logging.error( 'Unexpected key error %s' % (ke,))
                except UnicodeEncodeError as uee:
                    logging.error( 'Unicode error %s %s' % (uee,filename))

    def sqlite_details(self,conn,ref):
        dpi = self.args.dpi
        filename = os.path.basename(self.filename)
        digits = self.barcode#.replace(',',';').replace(' ','')
        #digits = cleaned(digits)
        istr = "insert into vops values (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?)"
        cur = conn.cursor()
        for m in range(len(self.va)):
            try:
                contest2 = ref.va[m].contest_text
                choice = ref.va[m].choice_text#.replace('~','')
                #choice = choice.replace('@','')
                #choice = cleaned(choice)
                voted = int(self.va[m].marked)
                cur.execute(
                    istr,
                    (
                        filename,
                        digits,
                        contest2,
                        choice,
                        voted,
                        int(self.va[m].covered),
                        int(self.va[m].x),
                        int(self.va[m].y),
                        int(self.va[m].w),
                        int(self.va[m].h),
                        int(self.va[m].overvoted),
                        int(self.va[m].undervoted),
                        self.rotation
                    )
                )
            except sqlite3.Error as sq_e:
                logging.error(
                    "Unexpected sqlite error %s %d %s." % (sq_e,m,filename))
            except IndexError as ie:
                logging.error(
                    "Unexpected Index Error %s %d %s" % (ie,m,filename))
            except KeyError as ke:
                logging.error( 'Unexpected key error %s' % (ke,))
            except UnicodeEncodeError as uee:
                logging.error( 'Unicode error %s %s' % (uee,filename))
        conn.commit()
        
    def set_coverage_range_and_marked(self,args):
        dpi = self.args.dpi
        threshold = args.coverage_threshold
        far_below_threshold = (95*threshold)/100
        vop_min_dark = args.box_dark_pixel_min
        self.lowest_coverage = 10000
        self.highest_coverage = 0
        template = '/media/mitch/Seagate_Backup_Plus_Drive/2018_June/%s/%s'
        base = os.path.basename(self.filename)
        cv2_im = self.tmp_cv2_im
        xvctr=0
        last_vy = 0
        for v in self.va:
            if v.covered >= vop_min_dark:
                xvctr += 1
                continue
            else:
                if cv2_im is None:
                    cv2_im = cv2.imread(self.filename)
                cropped_vop = cv2_im[v.y:v.y+v.h,v.x:v.x+v.w]
                extra_y = viu.cv2_first_hline_with_n_dark(
                    cropped_vop,
                    (args.nominal_width_of_vop)/2
                )

                extra_x = viu.cv2_first_vline_with_n_dark(
                    cropped_vop,
                    (args.nominal_height_of_vop)/2
                )

                if abs(extra_y) > 10:
                    logging.warning(
                        "extra_y %d (%d,%d,%d,%d)" % (
                            extra_y,v.x,v.y,v.x+v.w,v.y+v.h
                            )
                        )
                if abs(extra_x) >= (args.nominal_width_of_vop)/3: # sic 3
                    logging.warning(
                        "extra_x %d (%d,%d,%d,%d)" % (
                            extra_x,v.x,v.y,v.x+v.w,v.y+v.h
                            )
                        )
                v.y = v.y + extra_y
                v.x = v.x + extra_x
                self.va[xvctr].x = v.x
                if (v.y - last_vy) > 70: 
                    self.va[xvctr].y = v.y
                else:
                    logging.error("Two vops with y sep <= 70 at %s",self.filename)
                last_vy = v.y
                bp = (v.w+(2*args.vop_slack)) * (v.h+(2*args.vop_slack))
                bp -= count_white_cv2(cv2_im[v.y - args.vop_slack:v.y+v.h+args.vop_slack,v.x-args.vop_slack:v.x+v.w+args.vop_slack])
                if bp < vop_min_dark:
                    msg = "Low coverage in %s at vop %d (%d,%d,%d,%d,%d)"
                    self.va[xvctr].covered = bp
                    logging.error(
                        msg,
                        self.filename,
                        xvctr,
                        v.x,
                        v.y,
                        v.w,
                        v.h,
                        v.covered)
                else:
                    self.va[xvctr].covered = bp
                    msg = "Assigned %d to %d, %s" % (bp,xvctr,self.filename)
                    logging.warning(msg)
            xvctr += 1
        xvctr = 0
        for v in self.va:
            if v.covered > self.highest_coverage:
                self.highest_coverage = v.covered
                xvctr+=1
                continue
            if v.covered < self.lowest_coverage:
                self.lowest_coverage = v.covered
                xvctr+=1
                continue
            if v.covered < vop_min_dark:
                logging.error("Coverage below minimum vop dark pixels, unacceptable %s %d %d %d %d %d" % (self.filename,v.x,v.y,v.w,v.h,v.covered))
                xvctr+=1
                #raise ReconciliationError
        if self.lowest_coverage < ((87*threshold)/100):
            self.lowest_coverage = ((87*threshold)/100)
            
        span = self.highest_coverage - self.lowest_coverage
        vctr = 0
        # There is a zone of ambiguity caused by the different
        # coverages of unmarked voteops.  When the coverage
        # span on an individual ballot, the difference between
        # the heaviest mark and the lightest box, is less than
        # 1/3 of the required coverage, we should consider the
        # ballot marked where the coverage of a given voteop is
        # 13% or more higher than the lightest voteop.
        for v in self.va:
            try:
                if v.covered >= threshold:
                    try:
                        v.marked = 1
                    except AttributeError as aa:
                        logging.error("Unexpected attribute error in %s" % (self.filename,))
                elif v.covered < far_below_threshold: # below 95% of threshold
                    v.marked = 0
                elif span < 1000 and v.covered > (113*self.lowest_coverage)/100:
                    v.marked = 1
                    v.light = 1
                    logging.warning("Light, mark set based on 13 pct above lowest for %s at vote %d (from 0)" % (
                        self.filename,vctr))
                    # check remaining votes central region
                elif self.tmp_cv2_im is not None:
                    try:
                        bp = (v.h- (2*dpi/15)) * (v.w - (2*dpi/15))
                        bp -= count_white_cv2(
                            self.tmp_cv2_im[v.y+(dpi/15):v.y+v.h-(dpi/15),v.x+(dpi/15):v.x+v.w-(dpi/15)])
                        if bp > 30:
                            logging.warning("Light, mark set based on center for %s at vote %d (from 0)" % (self.filename,vctr))
                            v.marked = 1
                            v.light = bp
                            crop2.save('%s/center_%s_%d.jpg' % (
                                args.temp_dir,
                                os.path.basename(self.filename),
                                vctr
                            )
                            )
                    except:
                        pass
                else:
                    v.marked = 0
            except AttributeError as a:
                print a,vctr,self.filename
                logging.error("Unexpected attribute error %s %d" % (self.filename,vctr))
            vctr = vctr + 1
            
    def remove_false_vops(self,ref):
        """Clean vote array of mistaken vop coords."""
        # In cases where someone fills in write-in names,
        # if they are the right size to be a vote op,
        # they will have been picked up by the connected comp
        # routine and must now be removed.
        dpi = self.args.dpi
        # Repeat until all false vops removed
        # but break after 40 tries to avoid potential loop
        # on incorrect True returns from cv2_false_vop
        for rep in range(40):
            if len(self.va) > len(ref.va):
                for n in range(len(self.va)):
                    if cv2_false_vop(self.tmp_cv2_im,self.va[n]):
                        self.va = self.va[0:n]+self.va[n+1:]
                        break

    def reconcile(self,ref,args):
        """Remove false vops, rebuild if vop array size doesn't match ref"""

        if len(self.va) > len(ref.va):
            self.remove_false_vops(ref)

        if len(self.va) != len(ref.va):
            try:
                self.rebuild_va_using_adjusted_ref_coords(ref)
                self.va_coords_from_reference = 1
            except ReconciliationError:
                raise ReconciliationError
        self.reconciled = self.reconciled + 1
        
    def split_big_boxes(self,im):
        """If big_boxes can be split into two vote op sized boxes, do that."""
        # Irrelevant at the moment
        for box in self.big_boxes:
            logging.debug("Big box (%d %d)" % (box[2], box[3]))
            
    def bprint(self):
        """Write ballot and voteop information to logger"""
        print("Ballot %s [%s]" % (
            self.filename,
            self.barcode)
        )
        for v in self.va:
            v.vprint()
        print( "End of ballot image" )

    def blog(self):
        """Write ballot and voteop information to logger"""
        logging.info("Ballot %s %s" % (self.filename,self.barcode))
        for v in self.va:
            v.vlog()
        logging.info( "End of ballot image" )
        
                
    def add_contest_text_where_blank(self):
        """Replace empty contest text with that of preceding vote op"""
        last_contest_text = ''
        vctr = 0
        dpi = self.args.dpi
        # We keep track of the va offsets at which the contest text changes
        # so that we will have ranges belonging to each contest,
        # making it possible to remove likely overvotes.

        for v in self.va:
            if v.contest_text == '':
                v.contest_text = last_contest_text
            else:
                self.contest_changes.append(vctr)
            last_contest_text = v.contest_text
            vctr = vctr + 1

    # Likely to be removed to a different process
    def find_overvotes(self,allowed_votes=1):
        """Find situations with more than one vote in a contest.
        If one vote is substantially less covered than others,
        remove it.  Otherwise, mark votes as overvoted.
        Must be generalized to handle contests allowing more than one choice.
        """
        dpi = self.args.dpi
        vctr = 0
        last_vctr = 0
        contest_votes = 0
        choice_coverage = []
        for v in self.va:
            if vctr in self.contest_changes:
                if contest_votes < 1 and vctr > 0:
                    self.va[vctr-1].undervoted = 1
                removed = False
                while contest_votes > allowed_votes : 
                    removed = False
                    min_choice_coverage = 10000
                    max_choice_coverage = 0
                    for cc in choice_coverage:
                        if cc < min_choice_coverage:
                            min_choice_coverage = cc
                        if cc > max_choice_coverage:
                            max_choice_coverage = cc
                    span = max_choice_coverage - min_choice_coverage
                    if span > (min_choice_coverage/2):
                        #unmark the lowest covered choice
                        #reduce contest_votes
                        for x in range(last_vctr,vctr):
                            if self.va[x].covered==min_choice_coverage:
                                self.va[x].marked = 0
                                logging.warning(
                                    'Unmarking %s %s %s %d span (%d)' % (
                                        self.filename,self.va[x].contest_text,
                                        self.va[x].choice_text,
                                        self.va[x].covered,
                                        span
                                    )
                                )
                                contest_votes = contest_votes - 1
                                removed = True
                    if not removed:
                        break
                if contest_votes > allowed_votes:
                    for x in range(last_vctr,vctr):
                        if self.va[x].marked:
                            self.va[x].overvoted = contest_votes
                contest_votes = 0
                choice_coverage = []
                last_vctr = vctr
            if v.marked:
                contest_votes = contest_votes+1
                choice_coverage.append(v.covered)
            vctr = vctr + 1

    def copy_text_from(self,b):
        """Copy contest and choice text from first BallotImage in array"""
        dpi = self.args.dpi
        ref_len = len(b.va)
        my_len = len(self.va)
        if ref_len != my_len:
            logging.error( '%s bad va length of %d vs ref %d!' % (
                self.filename,
                my_len,
                ref_len)
            )
            raise ReconciliationError
        for n in range(ref_len):
            x_diff = abs(self.va[n].x - b.va[n].x)
            y_diff = abs(self.va[n].y - b.va[n].y)
            if (x_diff > (2*dpi/3) or y_diff > (dpi/3)):
                b.errors = b.errors + 1
                if b.errors == 20:
                    logging.error(
                        "More than 20 errors referenced %s " % (
                            b.filename
                        )
                    )
                try:
                    logging.warning( "SELF (%d,%d) REF (%d,%d)" % (
                        self.va[n].x, self.va[n].y,
                        b.va[n].x, b.va[n].y))
                except:
                    pass
                break
            else:
                self.va[n].contest_text = b.va[n].contest_text
                self.va[n].choice_text = b.va[n].choice_text
                # the reference line_above value need not be
                # precisely correct for self; it just needs
                # to be present and non-zero
                self.va[n].line_above = b.va[n].line_above

    def rebuild_va_using_adjusted_ref_coords(self,ref):
        held_va = self.va
        slack = self.args.vop_slack
        #print 'Self before',[(v.x,v.y) for v in self.va[-5:]]
        #print 'Ref before',[(v.x,v.y) for v in ref.va[-5:]]
        self.va = []
        for v in ref.va:
            tmpx,tmpy = viu.translate_xy_ref_to_image(
                v.x,v.y,
                ref.ulc_x,ref.ulc_y,
                self.ulc_x,self.ulc_y
            )
            ref_ydiff = ref.urc_y - ref.ulc_y
            self_ydiff = self.urc_y - self.ulc_y
            total_ydiff = self_ydiff - ref_ydiff
            adj_x, adj_y = viu.rotate_xy_ref_to_image(
                self.ulc_x,self.ulc_y,
                tmpx,tmpy,
                total_ydiff)
            """    
            print "New approach",adj_x, adj_y
            adj_x, adj_y = viu.ref_coord_to_image_coord(
                v.x,
                v.y,
                ref.ulc_x,
                ref.ulc_y,
                self.ulc_x,
                self.ulc_y,
                ref.urc_x - ref.ulc_x,
                ref.urc_y - ref.ulc_y,
                self.urc_x - self.ulc_x,
                self.urc_y - self.ulc_y
            )
            print "Orig approach",adj_x, adj_y
            pdb.set_trace()
            """
            # crop slack pixels early to pick up left edge if left of prediction
            cropped_vop = self.tmp_cv2_im[-slack+adj_y:slack+adj_y+ref.args.nominal_height_of_vop,-slack+adj_x:slack+adj_x+ref.args.nominal_width_of_vop]
            extra_y = viu.cv2_first_hline_with_n_dark(
                cropped_vop,
                (ref.args.nominal_width_of_vop)/2
            )
            extra_x = viu.cv2_first_vline_with_n_dark(
                cropped_vop,
                (ref.args.nominal_height_of_vop)/2
                )
            
            # reduce extra_x and extra_y by slack, since we started slack early
            extra_x -= slack
            extra_y -= slack
            if abs(extra_x) > (1+slack) or abs(extra_y) > (1+slack):
                msg_template = '%s near (%d,%d), ref %s, adj coord dx,dy (%d,%d)'
                msg = msg_template % (
                    os.path.basename(self.filename),
                    v.x,v.y,
                    os.path.basename(ref.filename),
                    extra_x,extra_y
                )
                if (
                        (abs(extra_x) > 6*slack)
                        or (abs(extra_y) > 3*slack)
                ):
                    if (abs(extra_y) > 20):
                        cv2.imwrite('cropped.jpg',cropped_vop)
                        print "*************************************"
                    print 'The following correction should not have been needed:'
                    logging.error(msg)
                    msg = msg_template % (
                        os.path.basename(self.filename),
                        v.x,v.y,
                        os.path.basename(ref.filename),
                        extra_x,extra_y
                    )
                    print msg

                else:
                    logging.warning(msg)
            new_v = VoteOp()
            new_v.x = adj_x + extra_x
            new_v.y = adj_y + extra_y
            new_v.w = ref.args.nominal_width_of_vop
            new_v.h = ref.args.nominal_height_of_vop
            new_v.covered = (new_v.h+(ref.args.vop_slack*2)) # h w/slack
            new_v.covered *= (new_v.w+(ref.args.vop_slack*2))# * w w/slack
            y1 = new_v.y - ref.args.vop_slack
            y2 = new_v.y + new_v.h + ref.args.vop_slack
            x1 = new_v.x - ref.args.vop_slack
            x2 = new_v.x + new_v.w + ref.args.vop_slack
            new_v.covered -= count_white_cv2(
                    self.tmp_cv2_im[y1:y2,x1:x2]
                )
            new_v.contest_text = v.contest_text
            new_v.choice_text = v.choice_text
            self.va.append(new_v)
            
    
    def get_voteops_no_text(self,bis,sized_right):
        rotation = self.rotation
        barcode = self.barcode
        image_name = self.filename 
        has_text = self.has_text 
        args = bis.args
        dpi = args.dpi
        marked_coverage = args.coverage_threshold
        last_x = -200 # to allow pickup of columns offset only 1/3 inch
        line_above = 0
        last_line_above = 0
        sixdpi = 6 * args.dpi
        thirddpi = args.dpi/3
        eighthdpi = args.dpi/8
        tenthdpi = args.dpi/10
        sixteenthdpi = args.dpi/16
        thirtiethdpi = args.dpi/30
        hundredthdpi = args.dpi/100
        minpix_width = args.minimum_width_of_vop
        maxpix_width = args.maximum_width_of_vop
        minpix_height = args.minimum_height_of_vop
        maxpix_height = args.maximum_height_of_vop

        # matching the reference array
        # x_offsets dictionary tracks number of right-sized glyphs
        # in 1/10" bands and is keyed by band
        x_offsets = [x[0]/(tenthdpi) for x in sized_right]
        x_offset_dict = {}
        x_offset_matched_multiple_dict = {}
        # find count of size matches in dpi/10 bands
        for x in x_offsets:
            if x not in x_offset_dict.keys():
                x_offset_dict[x] = 1
            else:
                x_offset_dict[x] = x_offset_dict[x]+1
        for x in x_offset_dict.keys():
            if x_offset_dict[x]>1:
                x_offset_matched_multiple_dict[x] = 1
            try:
                if x_offset_dict[x]==1 and x_offset_dict[x+1]==1:
                    x_offset_matched_multiple_dict[x] = 1
            except:
                pass

        # dpi/10 bands with more than one size match are likely valid,
        # as may be 1/10" bands that are off off by one

        contest_ctr = 0
        choice_ctr = 0
        for x in sized_right:
            # vops must have sufficient dark pixels
            # to count
            if x[4] < 2000: # !!!! replace value with cl arg
                continue
            xdivtenthdpi = x[0]/tenthdpi
            if not (
                    xdivtenthdpi in x_offset_matched_multiple_dict.keys()
                    or (xdivtenthdpi+1) in x_offset_matched_multiple_dict.keys()
                    or (xdivtenthdpi-1) in x_offset_matched_multiple_dict.keys()
                    ):
                logging.info("%s %s as out of band in %s" % (
                    'Rejected right-sized potential vote op',
                    x,
                    image_name
                )
                )
                self.out_of_band.append(x)
                continue

            # likely vote op
            # clean up x offset, or reset column
            absdiff = abs(x[0]-last_x)
            minof2 = min(last_x,x[0])
            maxof2 = max(last_x,x[0])
            if ((absdiff >= thirtiethdpi) and (last_x > 0)):
                if ((absdiff > eighthdpi) and (absdiff < (args.dpi))):
                    logging.warning('%s %d diff %d' % (
                        "Invalid x offset, ",
                        minof2,absdiff
                    )
                    )
                    if x[1] < args.minimum_y_of_vop or x[1] > args.maximum_y_of_vop:
                        continue
                    else:
                        print x[1]
                        print "InvalidBoxOffsetError"
                        raise InvalidBoxOffsetError
                elif absdiff>=args.dpi:
                    pass
                else:
                    # presumably, this sort of difference is due to
                    # a voter marking to the left of the box, so
                    # rely on the x offset of the prior box
                    logging.debug("%s %d %s %d" % (
                        "Invalid x offset ",
                        minof2,
                        "(marking left of box)? Use prior",
                        maxof2))

            # if there is a minimum value of y for legitimate voteops,
            # don't save anything that does not meet or exceed it
            if x[1] < args.minimum_y_of_vop:
                continue
            if x[1] > args.maximum_y_of_vop:
                continue
            # create voteop and set whether marked from coverage field, x[4]
            # note that marked may not indicate a vote
            # in case of overvote in contest;
            # the (dpi/6)+(dpi/60) works out to 55 pixels at 300 dpi,
            # and a 55 pixel height will likely have more pixels darkened
            # by the box than a 54 pixel height, so light coverage is
            # more likely to represent a vote.
            v = VoteOp()
            v.x = x[0]
            v.y = x[1]
            v.w = x[2]
            v.h = x[3]
            v.covered = x[4]

            if len(self.va)>0:
                # Drops in x location of less than a tenth of an inch
                # that take place within a column are probably due to
                # voter writing outside box boundary, so we clean them up.
                if (v.y > self.va[-1].y 
                    and v.x < (self.va[-1].x - thirtiethdpi)
                    and v.x > (self.va[-1].x - (dpi/10) )
                ) :
                    v.x = self.va[-1].x
                # Non-minor increases in x of less than an inch
                # are never real
                if (
                        v.x > (self.va[-1].x + (dpi/10))
                        and v.x < (self.va[-1].x + dpi)
                        and (abs(v.y - self.va[-1].y) < dpi)
                ):
                    msg_template = 'Skipping likely non-vop after %d in %s' 
                    logging.info(
                        msg_template % (len(self.va),
                                        self.filename
                        )
                    )
                    continue
            # vops must be past image margin to count
            if v.x >= (self.args.minimum_x_of_vop):
                self.va.append(v)

    

    def get_voteops_text(self,bis):
        """Retrieve text for an image"""
        rotation = self.rotation
        barcode = self.barcode
        print 'Getting text for barcode',
        print barcode,time.strftime("%Y-%m-%d %H:%M:%S")

        image_name = self.filename 
        has_text = self.has_text 
        args = self.args
        dpi = args.dpi
        marked_coverage = args.coverage_threshold
        last_x = -200
        line_above = 0
        last_line_above = 0
        last_contest_text = ''
        sixdpi = 6 * args.dpi
        thirddpi = args.dpi/3
        eighthdpi = args.dpi/8
        tenthdpi = args.dpi/10
        sixteenthdpi = args.dpi/16
        thirtiethdpi = args.dpi/30
        hundredthdpi = args.dpi/100
        minpix_width = args.minimum_width_of_vop
        maxpix_width = args.maximum_width_of_vop
        minpix_height = args.minimum_height_of_vop
        maxpix_height = args.maximum_height_of_vop

        ptr_xywh = args.precinct_text_region_xywh
        x1 = ptr_xywh[0] + self.ulc_x
        x2 = x1 + ptr_xywh[2] 
        y1 = ptr_xywh[1] + self.ulc_y
        y2 = y1 + ptr_xywh[3]
        # !!!! make dilation dependent on dpi and boldness of text
        precinct_region = cv2.dilate(self.tmp_cv2_im[y1:y2,x1:x2],
                             np.ones((2,2),np.uint8))
        #precinct_region = self.tmp_cv2_im[y1:y2,x1:x2]
        # Note that precinct text is currently of dubious use, due to italics
        self.precinct_text = pytesseract.image_to_string(precinct_region,
                                    config='--psm 7')
        # take material after (Pre)'cin' and, where found, trim 'ct'
        try:
            self.precinct_text = self.precinct_text.encode('latin1')
            self.precinct_text = self.precinct_text.split('cin')[1]
            if "ct " in self.precinct_text:
                self.precinct_text = self.precinct_text[3:]
            elif "ct. " in self.precinct_text:
                self.precinct_text = self.precinct_text[3:]
            elif "c! " in self.precinct_text:
                self.precinct_text = self.precinct_text[3:]
            self.precinct_text = self.precinct_text.split('\n')[0]
        except:
            pass
        dilated = cv2.dilate(self.tmp_cv2_im,np.ones((1,10),np.uint8))
        dilated = cv2.bitwise_not(dilated)
        dilated_output = cv2.connectedComponentsWithStats(
                                    dilated,8,cv2.CV_32S)[2]
        # look for lines wider than an inch
        # in the dilated image
        dilated_stats = [x for x in dilated_output if x[0]>(dpi/3) and x[1]>(dpi/3) and x[2]>dpi]
        ds = sorted(dilated_stats,key=sortbyfields02)
        contest_ctr = 0
        choice_ctr = 0
        #valid_vop_x_offsets = #viu.find_correct_x_offsets_in(self.tmp_cv2_im)
        valid_vop_x_offsets = self.tared_column_offsets
        if len(valid_vop_x_offsets) > 3:
            bis.unprocessed.append(self.filename)
            bis.unprocessed_barcode.append(self.barcode)
            raise ReconciliationError
            # shorter synonym
        im = self.tmp_cv2_im
        for n in range(len(self.va)):
            #assign vop x to closest in valid
            # if it is more than 1/10 and less than 1/2 dpi away
            for m in range(len(valid_vop_x_offsets)):
                diff = abs(self.va[n].x - valid_vop_x_offsets[m])
                if  diff < (dpi/2) and diff > tenthdpi:
                    msg = "Replaced bad vop %d x, %d in %s with %d" % (
                        n,
                        self.va[n].x,
                        self.filename,
                        valid_vop_x_offsets[m]
                    )
                    logging.warning(msg)
                    print msg
                    logging.warning(valid_vop_x_offsets)
                    self.va[n].x = valid_vop_x_offsets[m]
                    x1 = self.va[n].x + self.va[n].w + (dpi/60)
                    y1 = self.va[n].y - (dpi/30)
                    x2 = self.va[n].x + self.va[n].w + (2*dpi)
                    y2 = self.va[n].y + self.va[n].h + (dpi/30)
                    new_crop = self.tmp_cv2_im[y1:y2,x1:x2]

                    new_text = viu.cleaned(
                        pytesseract.image_to_string(
                            new_crop,
                            config='--psm 7')
                    )
                    if len(new_text)>=2:
                        self.va[n].choice_text = new_text
                    if self.va[n].x < (dpi/3):
                        pass
                    break

            if len(ds)>0:
                line_above = find_y_of_contest(
                    self.va[n].x,
                    self.va[n].y,
                    self.args.dpi,
                    ds)

            # get new contest text only when column or contest changes,
            # as determined by a new "line_above" or a substantially
            # different x offset of the new vote op from the prior
            if (abs(line_above - last_line_above)>(hundredthdpi)
                or abs(last_x - self.va[n].x)>args.dpi):
                last_line_above = line_above
                last_x = self.va[n].x
                try:
                    self.va[n].contest_text,contest_crop = get_contest_text(
                        self,
                        bis,
                        line_above,
                        self.va[n],
                        valid_vop_x_offsets,
                        last_contest_text
                    )

                except TypeError as te:
                    print te
                last_contest_text = self.va[n].contest_text

                # when getting text and therefore producing a reference
                # vote array, adjust the v.y to first line within initial
                # vote op crop that is long enough to be a voteop
                y1 = self.va[n].y
                y2 = y1 + self.va[n].h
                x1 = self.va[n].x
                x2 = x1 + self.va[n].w
                cropped_vop = self.tmp_cv2_im[y1:y2,x1:x2]
                extra_y = viu.cv2_first_hline_with_n_dark(
                    cropped_vop,
                    (args.nominal_width_of_vop)/2
                )
                extra_x = viu.cv2_first_vline_with_n_dark(
                    cropped_vop,
                    (args.nominal_height_of_vop)/2
                )
                if extra_y > 10:
                    logging.warning(
                        "extra_y %d %s (%d,%d,%d,%d)" % (
                            extra_y,
                            image_name,
                            self.va[n].x,
                            self.va[n].y,
                            self.va[n].x + self.va[n].w,
                            self.va[n].y + self.va[n].h
                        )
                    )
                if extra_x > 120:
                    logging.warning(
                        "extra_x %d %s (%d,%d,%d,%d)" % (
                            extra_x,
                            image_name,
                            self.va[n].x,
                            self.va[n].y,
                            self.va[n].x + self.va[n].w,
                            self.va[n].y + self.va[n].h
                        )
                    )
                self.va[n].y += extra_y
                self.va[n].x += extra_x
                contest_ctr = contest_ctr + 1

                if self.va[n].contest_text == '':
                    try:
                        if contest_crop is not None:
                            self.va[n].contest_text = viu.cleaned(
                                pytesseract.image_to_string(
                                    contest_crop
                                )
                            )
                    except TypeError as te:
                        print te
                    except Exception as ee:
                        print ee
                        self.va[n].contest_text = 'NOTEXTBETWEEN %d AND %d %d' % (
                            line_above,
                            self.va[n].x,
                            self.va[n].y
                        )
                    if self.va[n].contest_text == '':
                        pass


            # repeat the process above to gather choice_text
            # from the region to the right of the voteop;
            # this is done for all voteops, unlike contest_text
            choice_ctr = choice_ctr+1    
            self.va[n].line_above = line_above
            prior_choice_text = self.va[n].choice_text
            platter = cv2.bitwise_not(np.zeros((dpi,3*dpi), np.uint8))
            #platter = Image.new("1",(3*dpi,dpi),color=1)
            # we need to be careful here to avoid pulling in
            # more than one line's worth of choice text
            # when the voter marked outside the box 
            x1 = self.va[n].x + args.nominal_width_of_vop + (dpi/60)
            #self.va[n].w + (dpi/60)
            x2 = x1 + (2*dpi)
            y1 = self.va[n].y
            y2 = y1 + self.va[n].h
            if self.va[n].h <= (args.nominal_height_of_vop + (dpi/60)):
                plate = self.tmp_cv2_im[y1:y2,x1:x2]
            else:
                y1 -= (dpi/30)
                y2 += (dpi/30)
                plate = self.tmp_cv2_im[y1:y2,x1:x2]
            try:
                self.va[n].choice_text = viu.cleaned(
                    pytesseract.image_to_string(plate,config = '--psm 7')
                )
            except Exception as ee:
                print ee
                pass
            if self.va[n].choice_text == '':
                platter[50:50+plate.shape[0], 50:50+plate.shape[1]] = plate
                try:
                    self.va[n].choice_text = viu.cleaned(
                        pytesseract.image_to_string(platter)
                    )
                except Exception as ee:
                    print ee
                    pass
                if self.va[n].choice_text == '':
                    platter[50:50+plate.shape[0], 250:250+plate.shape[1]] = plate
                    try:
                        self.va[n].choice_text = viu.cleaned(
                            pytesseract.image_to_string(platter)
                        )
                    except Exception as ee:
                        print ee
                        pass
            if self.va[n].choice_text == '':
                self.va[n].choice_text = 'NONE%s' % (os.path.basename(self.filename)[:-4],)
            if self.barcode not in bis.image_dict:
                bis.image_dict[self.barcode] = []
            crop_im_small = cv2.resize(plate, (0,0), fx=0.25, fy=0.25)

            bis.image_dict[self.barcode].append([self.va[n].choice_text,crop_im_small])


def cv2_false_vop(cv2_im,v,n=50):
    crop = cv2_im[v.y:v.y+v.h,v.x:v.x+v.w]
    imheight,imwidth = cv2_im.shape
    retval = -1
    if imheight > 20:
        imheight = 20
    for y in range(imheight):
        s = cv2.sumElems(cv2.bitwise_not(crop[y:y+1,0:imwidth-1]))
        s = s[0]/255
        if s > n:
            retval = y
            break
    if retval == -1:
        return True
    return False

def count_white_cv2(cv2_img):
    """Return the number of pixels in img that have 0 value."""
    retval = 0
    retval = cv2.sumElems(cv2_img)
    retval = int(retval[0])/255
    return retval
        

        
def cleaned(t):
    """Return t cleaned of commas, newlines, and non-ASCII, in uppercase."""
    global cleanup_regex_string
    retval = None
    if not cleanup_regex_string:
        cleanup_regex_string = regex.compile(ur"[|\p{P}\p{S}]+")
    try:
        retval = regex.sub(cleanup_regex_string, "",t)
        retval = retval.replace('\n',' ').replace('  ',' ').strip().upper()
    except Exception as e:
        #pdb.set_trace()
        pass
    try:
        if retval[-1]=='\n':
            retval = retval[:-1]
    except Exception as e:
        pass
    return retval
