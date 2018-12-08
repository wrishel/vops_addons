# TEVS alternative vote counting program
# Copyright 2018 Mitch Trachtenberg, mjtrac@gmail.com
# Usage: python vops --dpi <dpi> --pathspec <pathspec of image files>


import cv2
import gc
import glob
import logging
import numpy as np
import os
import pickle
import pdb
import shutil
import sqlite3
import statistics
import sys
import tarfile
import time
from vops_error import ReconciliationError, BarcodeError, NoImageReadFromFileError, InvalidBoxOffsetError, CornerNotFoundError
from vops_parse import parse_command_line
from vops_bis import BallotImageSet
from vops_bi import BallotImage
import vops_image_util as viu
import vops_barcode
from vops_image_to_text_mappings import write_image_to_text_mappings
try:
    import pyodbc
except:
    print "Cannot import pyodbc."
    
dpi = 300
image_count = 0
repair_counter = 0
global template_ulc 
global template_urc 

def sortbyfields01(e):
    """Sort vertically within 600 pixel wide stripes (likely 2 inches)"""
    # because this is called a zillion times, don't bother with dpi
    # unless you can establish that doesn't slow things significantly
    return ((e[0]/600)*18000)+e[1]

def bia_median_va_length(bia):
    """From array of ballot inst's, get median length of their vote arrays"""
    va_lengths =[ len(bia[x].va) for x in range(len(bia)) ]
    med = statistics.median( va_lengths )
    med = int(round(med)) # note that int alone will round down
    logging.debug("Median %d %s" % (med,va_lengths))
    return med

def bia_has_contest_text(bia):
    """Determine if array of ballot inst's has text by testing first."""
    # Text, if present at all, is present in the first vop 
    # of the first ballot instance in the array of ballot instances
    # used by each barcode.
    try:
        retval = len(bia[0].va[0].contest_text) > 1
    except:
        retval = False
    return retval

def ballot_has_contest_text(ballot):
    """Determine if ballot inst has text by testing first vop."""
    # Text, if present at all, is present in the first vop 
    # of the first ballot instance in the array of ballot instances
    # used by each barcode.
    try:
        retval = len(ballot.va[0].contest_text) > 1
    except:
        retval = False
    return retval

def get_rightsized_cc(img_t_r,column_offsets,args):
    """Given a threshold image and column offsets, find vop-sized cc's"""
    backup = args.dpi/3
    advance = 2*backup
    zones = [(z - backup, z + advance) for z in column_offsets]
    minpix_width = args.minimum_width_of_vop
    maxpix_width = args.maximum_width_of_vop
    minpix_height = args.minimum_height_of_vop
    maxpix_height = args.maximum_height_of_vop
    image_zones = []
    outputs = []
    stat_groups = []
    return_stats = []
    for n in range(len(column_offsets)):
        image_zone = img_t_r[0:img_t_r.shape[0], zones[n][0]:zones[n][1]]
        outputs.append(
            cv2.connectedComponentsWithStats(image_zone,4,cv2.CV_32S)
        )
        stat_groups.append(outputs[n][2])
        stat_groups[n] = [[s[0]+zones[n][0],s[1],s[2],s[3],s[4]] for s in stat_groups[n] if s[2] >= minpix_width and s[2] <= maxpix_width and s[3] >= minpix_height and s[3] <= maxpix_height] 
        stat_groups[n] = sorted(stat_groups[n],key=sortbyfields01)
        return_stats.extend(stat_groups[n])
    return return_stats


def get_upper_coordinates(img_as_read,args,image_name):
    """Return ulc and urc coord pairs of box enclosing content of given image"""
    global template_ulc, template_urc
    ulc = []
    urc = []
    # This routine must compromise between searching a large region
    # and searching a smaller region for speed.  
    x1 = args.ulc_search_region_xywh[0]#((4*dpi)/10)
    y1 = args.ulc_search_region_xywh[1]
    x2 = x1 + args.ulc_search_region_xywh[2]
    y2 = y1 + args.ulc_search_region_xywh[3]
    if x2 >= img_as_read.shape[0]: print 'x2 >= shape zero'
    if y2 >= img_as_read.shape[1]: print 'y2 >= shape one'
    try:
        #cv2.imwrite('uppercorner.jpg',img_as_read[y1:y2,x1:x2])
        ulc = viu.find_ulc(
            img_as_read[y1:y2,x1:x2],
            template_ulc,
            args.dpi/75
        )
        ulc = [ulc[0]+x1,ulc[1]+y1]#[x+100 for x in ulc]
    except IndexError as ie:
        print ie
        logging.error('Index error at %s ' % (image_name,))
    
    im_height,im_width = img_as_read.shape[0:2]
    try:
        x1 = args.urc_search_region_xywh[0]#((4*dpi)/10)
        y1 = args.urc_search_region_xywh[1]
        x2 = x1 + args.urc_search_region_xywh[2]
        y2 = y1 + args.urc_search_region_xywh[3]
        urc = viu.find_urc(
            img_as_read[y1:y2,x1:x2],
            template_urc,
            args.dpi/75
        )
        urc = [urc[0]+x1,urc[1]+y1]
    except IndexError as ie:
        print ie
        logging.error('Index error at %s ' % (image_name,))

    urc_x = urc[0]
    urc_y = urc[1]
    ulc_x = ulc[0]
    ulc_y = ulc[1]
    upper_line_nominal_length = 7.37*args.dpi #im_width - (args.left_margin+args.right_margin) 
    apparent_line_length = urc_x - ulc_x
    dist_to_first_f = 60
    dist_to_second_f = 90
    dist_ave = (dist_to_first_f + dist_to_second_f)/2
    if  apparent_line_length < (upper_line_nominal_length - (args.dpi/10)):
        if abs(upper_line_nominal_length - apparent_line_length) > (dist_ave):
            # either ulc or urc is wrong;
            # PATCH
            # in Humboldt, 
            # most likely, an F in "OFFICIAL" was picked up as the ulc
            # so I'm patching by reducing ulc_y
            # by the distance between the F and
            # the actual ulc, 17 pixels on a 300 dpi image,
            # and reducing ulc_x by the distance between
            # the appropriate F and the actual ulc, 60 pix or 90 pix
            ulc = [ulc[0]-dist_to_second_f,ulc[1]-17]
        else:
            ulc = [ulc[0]-dist_to_first_f,ulc[1]-17]
            
    return ulc,urc

def process_one_image(args,bis,image_name):
    """Get votes and optionally text from an image"""
    global template_ulc, template_urc
    flipped = False
    dpi = args.dpi
    rotation = 0
    logging.info('Processing '+image_name)
    boxes = {}
    boxes['left'] = []
    boxes['top'] = []
    boxes['char'] = []

    co = 8

    # Read,tare, and threshold the desired image
    # img_as_read is unthresholded, img_thresh is thresholded
    img_as_read = cv2.imread(image_name,0)
    if img_as_read is None:
        raise NoImageReadFromFileError

    # We assume the top line will never be higher than 2/3"
    # or lower than 1" from the image top,
    # the upper left corner will never be closer than 1/3"
    # or farther than 11/12" from the left edge,
    # and the upper right corner will never be farther than 1"
    # or closer than 1/6" from the right edge.
    # ulc,urc upper left|right corner x,y coordinate pairs


    # a default darkness threshold of 192
    # picks up anything 1/4 or more darkened
    img_thresh = cv2.threshold(img_as_read,
                             args.darkness_threshold,
                             255,
                             cv2.THRESH_BINARY)[1]

    if img_thresh is None:
        raise NoImageReadFromFileError

    ulc, urc = get_upper_coordinates(img_as_read,args,image_name)
    bi = BallotImage()
    bi.ulc_x = ulc[0]
    bi.ulc_y = ulc[1]
    bi.urc_x = urc[0]
    bi.urc_y = urc[1]
    bi.tmp_cv2_im = img_thresh
    bi.flipped = flipped
    bi.args = args
    try:
        if abs(bi.ulc_y - bi.urc_y) > (args.dpi/20):
            msg = 'Derotating %s prior to barcoding due to skew > .05"' % (
                image_name,
            )
            logging.info(msg)
            bi.rotation = viu.ballot_get_skew_angle(bi)
            rows,cols = bi.tmp_cv2_im.shape
            M = cv2.getRotationMatrix2D((cols/2,rows/2),bi.rotation,1)
            img_thresh = cv2.warpAffine(img_thresh,M,(cols,rows))
            img_as_read = cv2.warpAffine(img_as_read,M,(cols,rows))
            bi.tmp_cv2_im = img_thresh#cv2.warpAffine(bi.tmp_cv2_im,M,(cols,rows))

            bi.rotated = bi.rotation
            bi.rotation = 0
            ulc, urc = get_upper_coordinates(img_as_read,args,image_name)
            if abs(ulc[1] - urc[1]) > (args.dpi/20):
                logging.error("Derotation failed at %s" % (image_name))
                bis.unprocessed.append(image_name)
                bis.unprocessed_barcode.append('?')
                raise CornerNotFoundError
            bi.ulc_x = ulc[0]
            bi.ulc_y = ulc[1]
            bi.urc_x = urc[0]
            bi.urc_y = urc[1]

    except KeyError as ex:
        logger.error(ex)
        return None
    try:
        barcode_string,flipped = vops_barcode.get_barcode(
            img_thresh,
            img_as_read,
            args,
            ulc,
            image_name)
    except BarcodeError:
        logging.error('Barcode Error at get_barcode %s' % (image_name,))
        raise 'Barcode Error'
    if flipped:
        # We need to reestablish upper left and right corners if we flip image.
        img_thresh = cv2.flip(img_thresh,-1)
        img_as_read = cv2.flip(img_as_read,-1)
        #im = im.transpose(Image.ROTATE_180)
        ulc, urc = get_upper_coordinates(img_as_read,args,image_name)
        bi.ulc_x = ulc[0]
        bi.ulc_y = ulc[1]
        bi.urc_x = urc[0]
        bi.urc_y = urc[1]

    image_time = time.time()


    if args.barcode_only == True:
        return None, barcode_string, None

    ############ FIND SUITABLE IMAGE FOR RETRIEVING TEXT ##############
    # We only want to acquire text once we have a reasonable
    # assumption that we have detected the correct number of voteops
    # meaning we must wait for a sample of 8 instances of images
    # with a given barcode before we call get_text on an image
    # whose count of voteops matches the median count of voteops
    # in our sample set.
    get_text = False
    med = 0

    if barcode_string in bis.d:
        # Only check vote array sizes on first
        # to seventh ballot images,
        # and only after seven ballot images have been stored,
        # and only if the 0th ballot image in this array
        # has a 0th voteop with no valid contest text,
        # meaning we haven't saved text yet.
        bc = barcode_string
        lenbia = len(bis.d[barcode_string])
        # Get text only when needed.
        if not bia_has_contest_text(bis.d[bc]):
            get_text = True
        try:
            pass
        except KeyError:
            pass

    logging.info("Reversing sense of img_thresh to get img.")
    precinct = ''
    bi.barcode = barcode_string
    bi.filename = image_name
    bi.has_text = False
    bi.flipped = flipped
    bi.tmp_cv2_im = img_thresh
    bi.args = args
    # Even when get_text is True,
    # we still make an initial call to get_voteops 
    # to determine the length of the vote array
    bi.tared_column_offsets = [(bi.ulc_x + coloff) for coloff in args.column_offsets]

    # reverse sense used in bounding box searches
    img_thresh_reversed = cv2.bitwise_not(img_thresh)
    s_stats = get_rightsized_cc(
        img_thresh_reversed,
        bi.tared_column_offsets,
        args)
    try:
        bi.get_voteops_no_text(bis, s_stats)
        bis.add(bi.barcode,bi)
    except KeyError as ex:
        logger.error(ex)
        return None
    
    if not get_text:
        return bi, med, flipped

    # now find first dark to right of barcode at two locations
    # by advancing from add_x for the width of a bar (plus),
    # and then looking for first dark.
    logging.info(
        "Length of new bi va is %d, median is %d" % (
            len(bi.va),med
        )
    )
    lenbisdbarcode = len(bis.d[bi.barcode])
    if (lenbisdbarcode == 8):
        med = bia_median_va_length(bis.d[bi.barcode])
        for ballotnum in range(lenbisdbarcode):
            # Skip problematic ballots when looking for text
            if len(bis.d[bi.barcode][ballotnum].va) != med:
                continue
            early_bi = bis.d[bi.barcode][ballotnum]
            """
            early_bi.rotation = viu.ballot_get_skew_angle(early_bi)
            rows,cols = early_bi.tmp_cv2_im.shape
            M = cv2.getRotationMatrix2D((cols/2,rows/2),bi.rotation,1)
            early_bi.tmp_cv2_im = cv2.warpAffine(
                early_bi.tmp_cv2_im,
                M,
                (cols,rows)
            )
            early_bi.rotated = early_bi.rotation
            early_bi.rotation = 0
            ulc, urc = get_upper_coordinates(early_bi.tmp_cv2_im,args,image_name)
            early_bi.ulc_x = ulc[0]
            early_bi.ulc_y = ulc[1]
            early_bi.urc_x = urc[0]
            early_bi.urc_y = urc[1]
            """
            try:
                if not ballot_has_contest_text(early_bi):
                    early_bi.correct_reference_va()
                    early_bi.get_voteops_text(bis)
                    early_bi.add_contest_text_where_blank()
                    bis.found_median_bi[barcode_string]=1
                # if a non-problem ballot now has text,
                # remove it from its position in the barcode's ballot array
                # move it to the start of the array.
                if ballotnum > 0:
                    try:
                        bis.d[bc] = bis.d[bc][0:ballotnum] + bis.d[bc][(ballotnum+1):]
                        bis.d[bc].insert(0,early_bi)
                    except:
                        pass
            except:
                logging.error(
                    'Trouble getting voteops for early_bi %s' % (
                        early_bi.filename,)
                )
            break
        
    return bi,med, flipped

def clean_contests_and_choices(bi):
    """Ensure no duplicate choices in contest and no commas in text."""
    last_choice = ''
    for x in range(len(bi.va)):
        try:
            bi.va[x].contest_text = bi.va[x].contest_text.replace(',',';')
            bi.va[x].choice_text = bi.va[x].choice_text.replace(',',';')
            if last_choice == bi.va[x].choice_text:
                bi.va[x].choice_text = bi.va[x].choice_text+'2'
            last_choice = bi.va[x].choice_text
        except Exception as ex:
            logging.error('Unexpected exception at %s %d' % (bi.filename,x))

def process_filelist(args,barcode_dict,sums_dict,bis):
    global image_count
    cleanup_files = []
    with open(args.filelist,'rb') as cl:
        cleanup_files = [cf[:-1] for cf in cl.readlines()]
    for x in cleanup_files:
        try:
            process_file(x,args,sums_dict,bis)
        except ReconciliationError as re:
            logging.error('Reconciliation error, process file, at %s' % (x,))
            #pdb.set_trace()
            #process_file(x,args,sums_dict,bis)
        except CornerNotFoundError as cnfe:
            logging.error('CornerNotFound error, process file, at %s' % (x,))
        except Exception as e:
            print e
            logging.error('Exception at process %s: %s' % (x,e))
            pass
        try:
            postprocess_file(bis)
        except ReconciliationError as re:
            logging.error('Reconciliation error, postproc file, at %s' % (x,))
        except Exception as e:
            print e
            logging.error('Exception at post %s %s' % (x,e))
    return image_count

def process_pathspec(args,sums_dict,bis):
    global image_count
    for x in glob.iglob(args.pathspec):
        try:
            process_file(x,args,sums_dict,bis)
        except ReconciliationError as re:
            logging.error('Reconciliation error, process file, at %s' % (x,))
            pdb.set_trace()
            process_file(x,args,sums_dict,bis)
        except CornerNotFoundError as cnfe:
            logging.error('CornerNotFound error, process file, at %s' % (x,))
        except Exception as e:
            print e
            logging.error('Exception at process %s: %s' % (x,e))
            pass
        try:
            postprocess_file(bis)
        except ReconciliationError as re:
            logging.error('Reconciliation error, postproc file, at %s' % (x,))
        except Exception as e:
            print e
            logging.error('Exception at post %s %s' % (x,e))
    return image_count

def postprocess_file(bis):
    global image_count
    image_count += 1
    if not (image_count % 100):
        gc.collect()
        print( "Processed %d images (using %d barcodes) at %s" % (
            image_count,
            len(bis.d.keys()),                
            time.strftime("%Y-%m-%d %H:%M:%S")
        )
        )
        if not (image_count % 1000):
            # Ensure images are garbase collected when not in use.
            for ke in bis.d.keys():
                if len(bis.d[ke])>8:
                    for i in bis.d[ke]:
                        if i.tmp_cv2_im is not None:
                            i.tmp_cv2_im = None
            print('Unprocessed count: %d at %s' % (
                len(bis.unprocessed),
                time.strftime("%Y-%m-%d %H:%M:%S")
            )
            )

def skip_file(image_name,args):
    """Based on cli odd/even arguments, return whether to skip file."""
    # assumes decimal digits in name before final extension
    if (args.odd):
        try:
            val = int(image_name.split('.')[0][-1])
            if (val/2)*2 == val:
                return True
        except:
            return True
    if (args.even):
        try:
            val = int(image_name.split('.')[0][-1])
            if (val/2)*2 != val:
                return True
        except:
            return True
    return False

def process_file(x,args,sums_dict,bis):
    """Process one image file."""
    global image_count
    current_folder = os.path.dirname(x)
    image_name = os.path.basename(x)

    if skip_file(image_name,args):
        return

    med = 0
    im = None
    bi = None

    try:
        # process_one_image processes the image to a ballot instance,
        # but does not try to ensure the ballot instance vote array
        # is a good match to others of its barcode
        bi,med,flipped = process_one_image(args,
                                           bis,
                                           '%s/%s' % (
                                               current_folder,
                                               image_name
                                           )
        )
    except TypeError as te:
        logging.error("(%s) TypeError in process_one_image for image %s %s" % (
            inr,
            image_name,
            te)
        )
    except CornerNotFoundError:
        logging.error(
            'Corner not found processing %s/%s' % (
                current_folder,image_name
            )
        )
        raise CornerNotFoundError
        return

    if args.barcode_only == True:
        print med,image_name
        return

    if bi.barcode not in bis.d:
        bis.d[bi.barcode] = []
        bis.counts_dict[bi.barcode] = 1

    ballots_for_this_barcode = len(bis.d[bi.barcode])
    try:
        # assume text for ballot image has been retrieved if the
        # first vote op's contest_text field has length > 1,
        # so enter this if statement only if:
        # text has been retrieved for this ballot image,
        # the image vote array size is reasonable, and
        # we still have fewer than 8 instances of this image's barcode
        if ( (len(bi.va)==med)
             and (len(bi.va[0].contest_text) > 1)
             and (ballots_for_this_barcode < 8)
        ):
            clean_contests_and_choices(bi)

            try:
                if ballots_for_this_barcode:
                    if bi.barcode not in bis.found_median_bi:
                        bis.add(bi.barcode,bi)
            except IndexError:
                logging.warning(
                    "Calling bis.add after index error in %s" % (bi.filename,)
                )
                bis.add(bi.barcode,bi)

        ballots_for_this_barcode = len(bis.d[bi.barcode])
        # On the eighth ballot for a given barcode,
        # if the barcode's found_median_bi has not been set,
        # if there is contest text on the ballot, it is a result
        # of an incomplete process and should be removed.
        # We then process the first eight ballots
        # when the eighth is encountered, or just this ballot
        # if it is after the eighth instance of the barcode.
        just_this_ballot = False
        if ballots_for_this_barcode == 8:
            ballotrangestart = 0
            ballotrangeend = 8
            if not bi.barcode in bis.found_median_bi:
                msg = "No median va ballot at front, barcode %s" % (bi.barcode,)
                print "Clearing initial contest text of bad ballot"
                bis.d[bi.barcode][0].va[0].contest_text = ''
                print msg
                logging.error(msg)
        elif ballots_for_this_barcode < 8:
            ballotrangestart = 0 #sic
            ballotrangeend = 0 #sic
        else:
            just_this_ballot = True
            ballotrangestart = 9999 #flag value otherwise unused
            ballotrangeend = 10000 #one greater than 9999
        b2rec = None
        # ballotnum will range from 0 to 8 
        # when the 8th instance of a barcode is processed;
        # it will be 9999 when subsequent ballots of that barcode
        # are processed
        for ballotnum in range(ballotrangestart,ballotrangeend):
            if just_this_ballot:
                b2rec = bi
            else: # early ballots
                b2rec = bis.d[bi.barcode][ballotnum]
            # initial reference ballot is the zeroth ballot
            # in the array of ballots whose barcode matches
            # that of the ballot to be reconciled (b2rec)
            reference_ballot = bis.d[b2rec.barcode][0]

            # if we reach this stage, text will be needed
            # in the reference ballot (head of barcode's ballot list)
            # so reposition another to the front if the current front
            # lacks text.  
            if not ballot_has_contest_text(reference_ballot):
                try:
                    for bcount in range(1,len(bis.d[b2rec.barcode])):
                        va_len = len(bis.d[b2rec.barcode][bcount].va) 
                        if va_len !=len(reference_ballot.va):
                            continue
                        reference_ballot = bis.d[b2rec.barcode][bcount]
                        # reposition new reference ballot to front
                        bis.d[b2rec] = bis.d[b2rec.barcode][1:bcount]+bis.d[b2rec.barcode][bcount+1:]
                        bis.d[b2rec.barcode].insert(0,reference_ballot)
                        break
                except Exception:
                    msg_template = 'Problem getting new ref ballot for %s %s.'
                    logging.error(
                        msg_template % (b2rec.filename,b2rec.barcode)
                    )
                        
                try:
                    reference_ballot.get_voteops_text(bis)
                    reference_ballot.add_contest_text_where_blank()
                except Exception:
                    msg_template = 'Problem getting new ref text for %s %s.' 
                    logging.error(
                         msg_template % (b2rec.filename,b2rec.barcode)
                        )

            # never occurs?
            if len(reference_ballot.va[0].contest_text)<1:
                try:
                    reference_ballot.get_voteops_text(bis)
                    reference_ballot.add_contest_text_where_blank()
                except Exception:
                    logging.error("Problem getting new reference ballot.")
            ### end never occurs?
            try:
                try:
                    # never occurs?
                    if ballotrangeend == 8:
                        if not ballot_has_contest_text(reference_ballot):
                            reference_ballot.get_voteops_text(bis)
                    # end never occurs?
                    b2rec.reconcile(reference_ballot,bi.args)

                except ReconciliationError as recon_error:
                    logging.error('ReconciliationError in call b2rec.reconcile from process_file, %s %s' % (recon_error,b2rec))
                    print recon_error
                    bis.unprocessed.append(bi.filename)
                    bis.unprocessed_barcode.append(b2rec.barcode)
                    continue

                if (len(b2rec.va) != len(reference_ballot.va)):
                    raise ReconciliationError                
                b2rec.set_coverage_range_and_marked(args)

                if (len(b2rec.va) != len(reference_ballot.va)):
                    raise ReconciliationError

                if ballotrangeend == 8 and ballotnum == 0:
                    reference_ballot.add_contest_text_where_blank()
                if ballotnum > 0:
                    if not ballot_has_contest_text(b2rec):
                        msg_template = 'Copying text to %d, %s from %s' 
                        msg =  msg_template % (
                            ballotnum,
                            b2rec.filename,
                            reference_ballot.filename
                        )
                        logging.info(msg)
                    b2rec.copy_text_from(reference_ballot)

                b2rec.find_overvotes()
                b2rec.gen_details(reference_ballot)
                b2rec.sqlite_details(conn,reference_ballot)
            except ReconciliationError as recon_error:
                logging.error(
                    '(%s) Reconciliation error %s' % (
                        inr,
                        b2rec.filename
                    )
                )
                bis.unprocessed.append(bi.filename)
                bis.unprocessed_barcode.append('?')
                continue
            except KeyError as ke:
                logging.error('(%s) KeyError at image %s barcode %s, %s' % (
                    "Multiple images skipped",
                    image_name,
                    b2rec.barcode,
                    ke))
            except AttributeError as ae:
                logging.error(
                    '(%s) Attribute error at reconcile, ballotnum=%d' % (
                        inr,
                        ballotnum
                    )
                )
                logging.error(
                    '(%s) AttributeError %s %s' % (
                        "Multiple images skipped",
                        b2rec.barcode,
                        ke
                    )
                )
        if ballotrangeend == 8:
            for ballotnum in range(len(bis.d[bi.barcode])):
                bis.d[bi.barcode][ballotnum].tmp_cv2_im = None
        if just_this_ballot:
            bi.tmp_cv2_im = None

    except ReconciliationError as recon_error:
        logging.error(
            '(%s) ReconciliationError in process_one_image, %s %s' % (
            inr,
            image_name,
            recon_error)
        )
        bis.unprocessed.append(image_name)
        try:
            bis.unprocessed_barcode.append(bi.barcode)
        except:
            bis.unprocessed_barcode.append('?')
            return
    except BarcodeError as be:
        logging.error(
            '(%s) did not process barcode for image %s %s' % (
                inr,
                image_name,
                be)
        )
        bis.unprocessed.append(image_name)
        bis.unprocessed_barcode.append('?')
        return
    except InvalidBoxOffsetError as iboe:
        logging.error(
            '(%s) for image %s %s' % (
                inr,
                image_name,
                iboe)
        )
        bis.unprocessed.append(image_name)
        bis.unprocessed_barcode.append('?')
        return
    except TypeError as te:
        logging.error(
            '(%s) TypeError after process_one_image, %s %s' % (
                inr,
                image_name,
                te)
        )
        bis.unprocessed.append(image_name)
        bis.unprocessed_barcode.append('?')
        return
    except NoImageReadFromFileError:
        logging.error(
            '(%s) Could not read image from file %s' % (
                inr,
                image_name)
        )
        bis.unprocessed.append(image_name)
        bis.unprocessed_barcode.append('?')
        return
    except IndexError as ie:
        logging.error(
            '(%s) Index error %s' % (
                inr,
                image_name,
            )
        )



if __name__ == "__main__":
    global template_ulc,template_urc
    inr = "Image not reported"

    # PARSE COMMAND LINE
    args = parse_command_line()

    # ESTABLISH LOGGING
    if args.log_file:
        logging.basicConfig(level=args.log_level_int,filename=args.log_file)
    logger = logging.getLogger()
    if args.vote_loc != 'l':
        print "Only votes to left of text can be counted at the moment."
        sys.exit(1)

    # CONNECT TO SQLITE, make connection available via args
    try:
        conn = sqlite3.connect('tevs.db')
        cursor = conn.cursor()
        cursor.execute("""
        create table if not exists vops (id integer primary key,filename text, subset_id text, contest_text text, choice_text text, marked integer, covered integer, x integer, y integer, w integer, h integer, overvoted integer, undervoted integer, rotation float)""")
    except :
        logging.error("SQLite error, will not use sqlite.")
        
    # UPDATE USER WITH ARGS AND TIME
    print "TEVS has begun processing files matching"
    print args.pathspec
    print "at",time.strftime("%Y-%m-%d %H:%M:%S")
    print "Specified or default arguments, with dimensions"
    print "converted from hundredths of an inch to pixel counts:"
    cli = [(i[0],i[1]) for i in args.__dict__.items()]
    cli.sort()           
    for k,v in cli: print k,'=',v   
    print
    print "Progress updates will print every 100 images."
    print "Counts will not be presented until the end."
    print



    # As results are written to details.csv, vote counts are captured here.
    sums_dict = {}
    
    # BallotImageSet contains a dictionary keyed on barcode,
    # with a BallotImage array for images with that barcode,
    # and processing routines to act on the arrays
    bis = BallotImageSet(args)
    #bis = pickle.load(open('bitest.pickle','rb'))
    # rename details.csv if it exists
    if os.path.isfile('details.csv'):
        os.rename('details.csv',
                  'details_backedup.%s.csv' % (time.strftime("%Y%m%d%H%M%S"))
                  )
    
    start_time = time.time()
    image_count = 0
    template_ulc = np.array(
        [
            [255, 255, 253, 254, 255, 255, 251, 255, 255, 255],
            [248,   1,   5,   0,   7,   0,   3,   0,   0,   0],
            [  3,   0,   4,   0,   0,   0,   0,   3,   0,   0],
            [  1,   0,   0,   7,   2,   3,   2,   0,   1,   1],
            [  0,   3,   0, 248, 255, 249, 255, 252, 254, 254],
            [  1,   4,   3, 255, 255, 253, 255, 252, 255, 255],
            [  0,   0,   3, 249, 255, 255, 247, 255, 255, 255],
            [  2,   0,   0, 255, 250, 255, 255, 254, 255, 255],
            [  0,   1,   0, 255, 255, 254, 255, 255, 255, 255],
            [  0,   1,   0, 255, 255, 254, 255, 255, 255, 255]
        ],
        dtype=np.uint8
    )

    template_urc = cv2.flip(template_ulc,1)
    if args.filelist:
        image_count = process_filelist(args,sums_dict,bis)
    else:
        image_count = process_pathspec(args,sums_dict,bis)


    

    print "Processed",image_count,"images at",time.strftime("%Y-%m-%d %H:%M:%S")
    print time.strftime("%Y-%m-%d %H:%M:%S")

    # the details file is now complete, and so this would be the place
    # to unify close strings using something like diffutils;
    # appropriate choices.txt file can be generated from details.csv with:
    #  cut -d , -f 4 details.csv | sort | uniq -c | sort -r -n | cut -c 9- > choices.txt
    # and can be used to generate a sedscript.txt to apply to details:
    """
    import difflib
    lines = []
    lines_orig = []
    with open('choices.txt','r') as f:
        lines = f.readlines()
    lines = [l[:-1] for l in lines]
    with open('sedscript.txt','w') as f:
        while len(lines)>0:
            print "Remaining lines",len(lines)
            line = lines[0]
            if not line:
                break
            cm = difflib.get_close_matches(line,lines,n=4,cutoff=0.8)
            replacement = line
            for m in cm:
                try:
                    lines.remove(line)
                except ValueError:
                    pass
                if m != line:
                    f.write('s/,%s,/,%s,/\n' % (m,replacement))
                lines = [l for l in lines if l != m]
    print "Done writing sedscript.txt"
    """
    # once details.csv has been processed through this sedscript,
    # counts can be generated based on fields 3,4,5 (numbering from 1)

    for k in bis.d.keys():
        if len(bis.d[k]) < 8:
            logging.error('Fewer than 8 instances of barcode %s ' % (k,))
            for bi in bis.d[k]:
                logging.error("Did not report out %s" % (bi.filename,))

    print 'Clearing images prior to pickling.'
    for k in bis.d.keys():
        for bi in bis.d[k]:
            bi.tmp_cv2_im = None

    print 'Garbage collecting.'
    gc.collect()

    print 'Pickling to bi.pickle in working directory'
    with open('bi.pickle','wb') as f:
        pickle.dump(bis,f)
    print "Pickled at",time.strftime("%Y-%m-%d %H:%M:%S")
    print time.strftime("%Y-%m-%d %H:%M:%S")

    print 'Saving archive file of temporary images in working directory'
    gc.collect()
    with tarfile.open('tempdir_images.tgz','w:gz') as tf:
        for name in os.listdir(args.temp_dir):
            fullname = '%s/%s' % (args.temp_dir,name)
            tf.add(fullname)
    print "Temp images tarred at",time.strftime("%Y-%m-%d %H:%M:%S")

    write_image_to_text_mappings(bis.image_dict)


    print "Removing temporary directory",args.temp_dir
    shutil.rmtree(args.temp_dir)

    print "Barcodes and files with fewer than 8 instances of barcode"
    print "Until remedied in this program, these can most easily"
    print "be handled by cloning the named files to create barcode groups"
    print "with at least eight instances, and rerunning this program"
    print "on those files only."
    for bc in bis.d.keys():
        if len(bis.d[bc]) < 8:
            for bi in bis.d[bc]:
                print bi.barcode,bi.filename
    print "Files not successfully processed"
    print bis.unprocessed
    print bis.unprocessed_barcode
    print "Exiting."
    sys.exit(0)


        
