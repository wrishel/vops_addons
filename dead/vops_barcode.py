import cv2
import logging
import numpy as np
from PIL import Image
from pyzbar import pyzbar
from vops_error import  BarcodeError


# Assumptions made here:
# the correct barcode will have 14 digits,
# the leading digit will be 1 or 2,
# and the barcode is present 1/4" to left
# of the upper left corner of the ballot's
# enclosing box.

def barcode_upright_image(dpi,im,bc_x,bc_y,bc_width,bc_height):
    """Return barcode at ulc of image and x offset of barcode"""
    # try for barcode at 1/15 inch intervals
    # from 1/8 to a full inch from left
    flipped = False
    valid_barcode_pattern_length = 77
    barcode_x_offset = dpi/8
    add_x = 0
    ret_y = 0
    for add_x in range(bc_x,bc_x + bc_width,dpi/15):
        barcode = im[bc_y:bc_y + bc_height,add_x:add_x+1]
        barcode_string,ret_y = get_barcode_pattern(dpi,barcode)
        if len(barcode_string) >= valid_barcode_pattern_length:
            barcode_digits = barcode_to_digits_util(barcode_string)
            if (len(barcode_digits)==14
                and (barcode_digits[0]=='1' or barcode_digits[0]=='2')):
                break
        barcode_x_offset = add_x
    barcode_string = barcode_to_digits_util(barcode_string)
    return barcode_string, add_x


def get_barcode_pattern(dpi,barcode):
    """Get pattern of thick and thin black and white pixel seqs in barcode.
       Also, report y offset of first barcode pixel.
    """
    last = 'X' # skipping range of white pixels
    count = 0
    thick_thin_threshold = dpi/30
    barcode_string = ''
    letters = 'BW'
    #barcode.save('barcode.jpg')
    # skip black pixels
    for y in range((5*dpi/2)-1,(5*dpi/2)-50,-1):
        if barcode[y,0] < 128:
        #if not barcode.getpixel((0,y)):
            pass
        first_white = y
        break
    # skip white pixels
    first_black = 0
    for y in range(first_white,0,-1):
        if barcode[y,0] > 128:
        #if (barcode.getpixel((0,y))):
            pass
        else:
            first_black = y
            break
    count = 0
    ret_y = 0
    for y in range(first_black,0,-1):
        count = count + 1
        #handle stray dark pixels before/after barcode
        if (count > (3*thick_thin_threshold)):
            last = 'W'
            count = 1
            if len(barcode_string)>=70:
                return barcode_string, ret_y
            barcode_string = ''
            ret_y = y
            continue
        
        # barcode.getpixel() will be 0 or 255
        #if (barcode.getpixel((0,y))):
        if barcode[y,0] > 128:
            if 'B' in last:
                barcode_string += 'B' if (count>thick_thin_threshold) else 'b'
                count = 1
                last = 'W'
        else:
            if 'W' in last:
                barcode_string += 'W' if (count>thick_thin_threshold) else 'w'
                count = 1
                last = 'B'
            elif 'X' in last:
                count = 1
                last = 'B'
    if last=='W':
        barcode_string+= 'W' if (count>thick_thin_threshold) else 'w'
    if last=='B':
        barcode_string+= 'B' if (count>thick_thin_threshold) else 'b'
    return barcode_string, ret_y

def barcode_to_digits_util(barcode_string):
    """Convert Hart style interleaved 2 of 5 barcode to populate barcode_digits field"""
    if len(barcode_string)<77:
        return '0'
    barcode = ''
    bwbw_forward = barcode_string.find('bwbw')
    if (bwbw_forward == 0 or bwbw_forward == 1):
        barcode = barcode_string[bwbw_forward+4:]
    else:
        raise BarcodeError
    
    digits = ''
    x = 0
    barcode = barcode+'w        '
    for x in range(0,70,10):
        if (barcode[x].islower()
            and barcode[x+2].islower()
            and barcode[x+4].isupper()
            and barcode[x+6].isupper()
            and barcode[x+8].islower()):
            digits = digits + '0'
        elif (barcode[x].isupper()
            and barcode[x+2].islower()
            and barcode[x+4].islower()
            and barcode[x+6].islower()
            and barcode[x+8].isupper()):
            digits = digits + '1'
        elif (barcode[x].islower()
            and barcode[x+2].isupper()
            and barcode[x+4].islower()
            and barcode[x+6].islower()
            and barcode[x+8].isupper()):
            digits = digits + '2'
        elif (barcode[x].isupper()
            and barcode[x+2].isupper()
            and barcode[x+4].islower()
            and barcode[x+6].islower()
            and barcode[x+8].islower()):
            digits = digits + '3'
        elif (barcode[x].islower()
            and barcode[x+2].islower()
            and barcode[x+4].isupper()
            and barcode[x+6].islower()
            and barcode[x+8].isupper()):
            digits = digits + '4'
        elif (barcode[x].isupper()
            and barcode[x+2].islower()
            and barcode[x+4].isupper()
            and barcode[x+6].islower()
            and barcode[x+8].islower()):
            digits = digits + '5'
        elif (barcode[x].islower()
            and barcode[x+2].isupper()
            and barcode[x+4].isupper()
            and barcode[x+6].islower()
            and barcode[x+8].islower()):
            digits = digits + '6'
        elif (barcode[x].islower()
            and barcode[x+2].islower()
            and barcode[x+4].islower()
            and barcode[x+6].isupper()
            and barcode[x+8].isupper()):
            digits = digits + '7'
        elif (barcode[x].isupper()
            and barcode[x+2].islower()
            and barcode[x+4].islower()
            and barcode[x+6].isupper()
            and barcode[x+8].islower()):
            digits = digits + '8'
        elif (barcode[x].islower()
            and barcode[x+2].isupper()
            and barcode[x+4].islower()
            and barcode[x+6].isupper()
            and barcode[x+8].islower()):
            digits = digits + '9'
        xplus = x+1
        if (barcode[xplus].islower()
            and barcode[xplus+2].islower()
            and barcode[xplus+4].isupper()
            and barcode[xplus+6].isupper()
            and barcode[xplus+8].islower()):
            digits = digits + '0'
        elif (barcode[xplus].isupper()
            and barcode[xplus+2].islower()
            and barcode[xplus+4].islower()
            and barcode[xplus+6].islower()
            and barcode[xplus+8].isupper()):
            digits = digits + '1'
        elif (barcode[xplus].islower()
            and barcode[xplus+2].isupper()
            and barcode[xplus+4].islower()
            and barcode[xplus+6].islower()
            and barcode[xplus+8].isupper()):
            digits = digits + '2'
        elif (barcode[xplus].isupper()
            and barcode[xplus+2].isupper()
            and barcode[xplus+4].islower()
            and barcode[xplus+6].islower()
            and barcode[xplus+8].islower()):
            digits = digits + '3'
        elif (barcode[xplus].islower()
            and barcode[xplus+2].islower()
            and barcode[xplus+4].isupper()
            and barcode[xplus+6].islower()
            and barcode[xplus+8].isupper()):
            digits = digits + '4'
        elif (barcode[xplus].isupper()
            and barcode[xplus+2].islower()
            and barcode[xplus+4].isupper()
            and barcode[xplus+6].islower()
            and barcode[xplus+8].islower()):
            digits = digits + '5'
        elif (barcode[xplus].islower()
            and barcode[xplus+2].isupper()
            and barcode[xplus+4].isupper()
            and barcode[xplus+6].islower()
            and barcode[xplus+8].islower()):
            digits = digits + '6'
        elif (barcode[xplus].islower()
            and barcode[xplus+2].islower()
            and barcode[xplus+4].islower()
            and barcode[xplus+6].isupper()
            and barcode[xplus+8].isupper()):
            digits = digits + '7'
        elif (barcode[xplus].isupper()
            and barcode[xplus+2].islower()
            and barcode[xplus+4].islower()
            and barcode[xplus+6].isupper()
            and barcode[xplus+8].islower()):
            digits = digits + '8'
        elif (barcode[xplus].islower()
            and barcode[xplus+2].isupper()
            and barcode[xplus+4].islower()
            and barcode[xplus+6].isupper()
            and barcode[xplus+8].islower()):
            digits = digits + '9'
        if len(digits)>=13:
            break
        # require barcodes to begin with 10 or 20,
        # so give up after first pass if that ain't happening
        try:
            if digits[0] != '1' and digits[0] != '2':
                break
            if digits[1] != '0':
                break
        except:
            pass
    return digits



def get_barcode(img_thresh,img_as_read,args,ulc,image_name):
    dpi = args.dpi
    barcode_xywh = args.barcode_region_xywh
    valid_barcode_pattern_length = 14
    barcode_string,add_x = barcode_upright_image(
        dpi,
        img_thresh,
        ulc[0] + barcode_xywh[0],
        ulc[1] + barcode_xywh[1],
        barcode_xywh[2],
        barcode_xywh[3]
    )
    flipped = False
    if len(barcode_string) != valid_barcode_pattern_length:
        # fall back to pyzbar before flipping
        logging.info(
            "%s barcoded by pyzbar,ulc x,y (%d %d)" % (
                image_name,ulc[0],ulc[1]
            )
        )
        img_crop = img_as_read[0:5*dpi, 0:dpi]
        im_pil = Image.fromarray(img_crop)
        try:
            decoded = pyzbar.decode(im_pil)
            barcode_string = decoded[0].data
        except:
            logging.error('try failed in pyzbar decode1')
            pass
    if len(barcode_string) != valid_barcode_pattern_length:
        logging.info(
            'Categorizing ULC barcode not found in %s, flipping' % (
                image_name,
            )
        )
        flipped = True
        img_thresh = cv2.flip(img_thresh,-1)
        img_as_read = cv2.flip(img_as_read,-1)
        img_crop = img_as_read[0:5*dpi, 0:dpi]
        im_pil = Image.fromarray(img_crop)
        try:
            barcode_string = pyzbar.decode(im_pil)[0].data
        except:
            logging.error('try failed in call to pyzbar.decode 2')
            raise BarcodeError
    return barcode_string, flipped
