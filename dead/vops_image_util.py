import cv2
import logging
import math
from math import sin, cos, atan2
import numpy as np
import pdb
import regex 
import time
from vops_error import CornerNotFoundError
cleanup_regex_string = None
dpi = 300

def translate_xy_ref_to_image(x,y,tmpl_x0,tmpl_y0,this_x0,this_y0):
    "Subtract tmpl tare x and y , add this tare x and y"
    # when x is 100 on an image whose ulc_x is 10,
    # it should be 110 on an image whose ulc_x is 20
    #print "Translate %d %d in tmpl orig  %d %d to img %d %d" % (x,y,tmpl_x0,tmpl_y0,this_x0,this_y0)
    x = x - tmpl_x0 + this_x0
    y = y - tmpl_y0 + this_y0
    return (x,y)
    

def rotate_xy_ref_to_image(x0,y0,x1,y1,ydiff):
    "Rotate x1,y1 about x0,y0 to compensate for urc ydiff"
    # Because we are in a flipped coord system,
    # flip all incoming y values, including the diff
    # and flip outbound y
    #print "Rotate x=",x1,"y=",y1, "about x=",x0,"y=",y0,"to compensate for ",ydiff
    angle = math.atan2(-ydiff,2000.)
    s = math.sin(angle)
    c = math.cos(angle)
    dx = x1-x0
    dy = -(y1-y0)
    xnew = dx*c - dy*s
    ynew = dx*s + dy*c
    xnew += x0
    ynew += -(y0)
    return (int(round(xnew)),int(round(-ynew)))


def ref_coord_to_image_coord(tmpl_vx,tmpl_vy,tmpl_x0,tmpl_y0,this_x0,this_y0,refxdiff,refydiff,xdiff,ydiff):
    """Given x,y as the upper left corner of a template voteop 
       on an image whose upper left corner is tmpl_x0, tmpl_y0,
       and given xdiff,ydiff as the x1-x0 and y1 - y0 of the 
       upper boxline of the given image, and given this_x0, this_y0
       as the upper left corner of the given image's upper boxline,
       return the location at which the vote op will be found
       on the given image.
    """
    theta = atan2(ydiff-refydiff,xdiff)
    #theta = atan2(ydiff,xdiff)
    x2 = int(round((tmpl_vx-tmpl_x0)*cos(theta) - (tmpl_vy-tmpl_y0)*sin(theta)))
    y2 = int(round((tmpl_vx-tmpl_x0)*sin(theta) + (tmpl_vy-tmpl_y0)*cos(theta)))
    return (x2+this_x0,y2+this_y0)

def find_ulc(img,template,ltip): 
    """Return x,y of upper left hand corner of ballot's enclosing box.

       Locates y offset of top line, crops shortly beneath that line
       to avoid exposure to capital-F, which masquerades as a corner,
       and finds pixel with best match to template of upper left corner.
    """
    # ltip = line thickness in pixels
    # first, find the first y that is dark when x is at/near the max
    threshold = 96
    img_rowcount = img.shape[0]
    img_colcount = img.shape[1]
    retval = None
    
    # search first for a 2x2 box of dark pixels
    # which will occur when horizontal line is reached
    # as well as at other times
    for i in range(ltip,img_rowcount-ltip-1):
        try:
            if (
                    (img[i-1,img_colcount-1] < threshold)
                    and (img[i,img_colcount-1] < threshold)
            ):
                if (
                        (img[i-1,img_colcount - 2 ] < threshold)
                        and (img[i,img_colcount - 2] < threshold)
                ):
                    # check whether y offset i
                    # leads to the corner
                    # by decreasing x
                    # and confirming continued dark pixels
                    # until a vertical line is found.
                    for j in range(img_colcount - ((2*ltip) + 2 + 1), 0, -1):
                        #print i,j
                        if img[i-1,j] > threshold and img[i,j] < threshold:
                            #line moving upwards?
                            if img[i-1,j] < threshold: i -= 1
                        elif img[i-1,j] < threshold and img[i,j] > threshold:
                            #line moving downwards?
                            if img[i+1,j] < threshold: i += 1
                        elif img[i-1,j] > threshold and img[i,j] > threshold:
                            # line may have ended here, look underneath
                            # to check for vertical line
                            # edge at one and two line thicknesses below
                            if (
                                    ((i + (ltip*2)) < img_rowcount)
                                    and (
                                        (img[i+(ltip*2),j] < threshold)
                                        or (img[i+(ltip*2),j+1] < threshold)
                                        or (img[i+(ltip*2),j+2] < threshold)
                                    )
                            ):
                                if (
                                        (img[i+ltip+1,j] < threshold)
                                        and (img[i+ltip+1,j+(2*ltip)] > threshold)
                                        ):
                                    retval = (j,i-2) # i and i-1 are known dark
                                elif (
                                        (img[i+ltip+1,j+1] < threshold)
                                        and (j < (img_colcount-((2*ltip)+2)))
                                        and (img[i+ltip+1,j+(2*ltip)+1] > threshold)
                                ):
                                    retval = (j+1,i-2)
                                elif (
                                        (img[i+ltip+1,j+2] < threshold)
                                        and (j < (img_colcount-((2*ltip)+3)))
                                        and (img[i+ltip+1,j+(2*ltip)+2] > threshold)
                                ):
                                    retval = (j+2,i-2)
                        if retval:
                            break
                    if retval:
                        break
        except IndexError:
            pdb.set_trace()
    if retval:
        return retval
    else:
        result = cv2.matchTemplate(img,
                               template,
                               cv2.TM_CCOEFF_NORMED)
            
        minVal,maxVal,minLoc,maxLoc = cv2.minMaxLoc(result)
        return maxLoc

def find_urc(img,urc_template,ltip):
    """Find upper right corner of box enclosing ballot's contents."""
    # ltip = line thickness in pixels
    # first, find the first y that is dark when x is at/near the max
    threshold = 128
    img_rowcount = img.shape[0]
    img_colcount = img.shape[1]
    retval = None
    
    # search first for a 2x2 box of dark pixels
    # which will occur when horizontal line is reached
    # as well as at other times
    for i in range(ltip,img_rowcount-ltip-1):
        try:
            if (
                    (img[i-1,1] < threshold)
                    and (img[i,1] < threshold)
            ):
                if (
                        (img[i-1,2 ] < threshold)
                        and (img[i,2] < threshold)
                        and (img[i,3] < threshold)
                        and (img[i-1,3] < threshold)
                ):
                    # check whether y offset i
                    # leads to the corner
                    # by decreasing x
                    # and confirming continued dark pixels
                    # until a vertical line is found.
                    for j in range(4,img_colcount - 4):
                        if img[i-1,j] > threshold and img[i,j] < threshold:
                            #line moving upwards?
                            if img[i-1,j] < threshold: i -= 1
                        elif img[i-1,j] < threshold and img[i,j] > threshold:
                            #line moving downwards?
                            if img[i+1,j] < threshold: i += 1
                        elif img[i-1,j] > threshold and img[i,j] > threshold:
                            # line may have ended here, look underneath
                            # to check for vertical line
                            # edge at one and two line thicknesses below
                            if (
                                    ((i + (ltip*2)) < img_rowcount)
                                    and (
                                        (img[i+(ltip*2),j] < threshold)
                                        or (img[i+(ltip*2),j-1] < threshold)
                                        or (img[i+(ltip*2),j-2] < threshold)
                                    )
                            ):
                                if (
                                        (img[i+ltip+1,j] < threshold)
                                        and (img[i+ltip+1,j+(2*ltip)] > threshold)
                                        ):
                                    retval = (j,i-2) # i and i-1 are known dark
                                elif (
                                        (img[i+ltip+1,j-1] < threshold)
                                        and (j < img_colcount-4)
                                        and (img[i+ltip+1,j+(2*ltip)-1] > threshold)
                                ):
                                    retval = (j-1,i-2)
                                elif (
                                        j>1 and (img[i+ltip+1,j-2] < threshold)
                                        and (j < img_colcount-5)
                                        and (img[i+ltip+1,j+(2*ltip)-2] > threshold)
                                ):
                                    retval = (j-2,i-2)
                        if retval:
                            break
                    if retval:
                        break    
        except IndexError:
            pdb.set_trace()
    if retval:
        return retval
    else:
        result = cv2.matchTemplate(img,
                               urc_template,
                               cv2.TM_CCOEFF_NORMED)
            
        minVal,maxVal,minLoc,maxLoc = cv2.minMaxLoc(result)
        return maxLoc

def sortbyfields01(e):
    """Sort vertically within 300 pixel wide stripes (likely 1 or 2 inches)"""
    return ((e[0]/600)*18000)+e[1]


def ballot_get_skew_angle(bi):
    dpi = bi.args.dpi
    im = bi.tmp_cv2_im
    if im is None:
        logging.error("No image provided to get_skew_angle.")
        return 0
    rotation = 0

    xdiff = 0
    xdiff = bi.urc_x - bi.ulc_x
    ydiff = bi.urc_y - bi.ulc_y
    rotation = math.degrees(
        math.atan(float(ydiff)/xdiff)
    )
    return rotation



# replaced with command line argument, adjusted by ulc tare
def xxfind_correct_x_offsets_in(cv2_im):
    #get hline only image
    imheight,imwidth = cv2_im.shape[0:2]
    dilated = cv2.dilate(cv2_im,
                         np.ones((dpi/32,dpi/32),np.uint8)
    )
    dilated = cv2.bitwise_not(dilated)
    #cv2.imwrite('dilated.jpg',dilated)
    output = cv2.connectedComponentsWithStats(
            dilated,8,cv2.CV_32S)
    stats = output[2]
    s_stats = sorted(stats,key=sortbyfields01)
    vops = []
    for stat in s_stats:
        if stat[2]> 80 and stat[2]<100 and stat[3] > 30 and stat[3]<50:
            if stat[0] > 120 and stat[1]>dpi and stat[1]<(imheight-(2*dpi/3)):
                vops.append(stat[0])
    last_vop = vops[0]
    voprow_min = last_vop
    voprow_max = last_vop
    voprow_array = []
    for vop in vops:
        if abs(vop-last_vop) >= 30 and abs(vop-last_vop) <= 300:
            last_vop = vop
            continue
        if abs(vop-last_vop) < 30:
            if vop < voprow_min:
                voprow_min = vop
            elif vop > voprow_max:
                voprow_max = vop
            last_vop = vop
        else:
            last_vop = vop
            voprow_array.append((voprow_min+voprow_max)/2)
            voprow_min = vop
            voprow_max = vop
    voprow_array.append(((voprow_min+voprow_max)/2)-(dpi/64))
    return voprow_array    
    

def cv2_first_hline_with_n_dark(im,n):
    """Find distance to vertical start of vop."""
    imheight,imwidth = im.shape
    row_dark_count = 0
    retval = -1
    search_backwards = False
    nominal_height = 54
    boxbottom = False
    for y in range((imheight/2) - 1):
        s0 = cv2.sumElems(cv2.bitwise_not(im[y:y+1,0:imwidth-1]))
        s0 = s0[0]/255
        if s0 > n: 
            retval = y
            #make sure we didn't hit a scan line of a vop bottom
            for y2 in range(y,(imheight/2) - 1):
                s1 = cv2.sumElems(cv2.bitwise_not(im[y2:y2+1,0:imwidth-1]))
                s1 = s1[0]/255
                if s1 <= n:
                    # the current y2 can no longer be a box line
                    # so check an area 0.02" and 0.03" below this one;
                    # if either has enough darkened pixels to account
                    # for a box left / right wall, it was the top,
                    # otherwise, it was the bottom
                    boxbottom = False
                    try:
                        y3 = y2 + 5
                        s2 = cv2.sumElems(
                            cv2.bitwise_not(im[y3:y3+1,0:imwidth-1])
                        )
                        s2 = s2[0]/255
                        y4 = y2 + 9
                        s3 = cv2.sumElems(
                            cv2.bitwise_not(im[y4:y4+1,0:imwidth-1])
                        )
                        s3 = s3[0]/255
                        if s2 < 10 or s3 < 10 :
                            boxbottom = True
                            logging.warning("Vop bottom encountered searching for first hline,skipping 10 lines")
                            y2 += 10
                            #pdb.set_trace()
                            #cv2.imwrite('boxbot.jpg',im)
                        else:
                            break
                        # note that it might still be a boxbottom
                        # with a thick scribble beneath, need to check
                        # but that case is not handled yet.
                    except:
                        print "Unexpected error in cv2_first_hline..."
                        pdb.set_trace()
                if not boxbottom: break
            if not boxbottom: break
    if retval == -1:
        search_backwards = True
    if search_backwards:
        for y in range(imheight-1,(imheight/2) -1,-1):
            s3 = cv2.sumElems(cv2.bitwise_not(im[y:y+1,0:imwidth-1]))
            s3 = s3[0]/255
            if s3 > n:
                retval = y - imheight
                break
    return retval

def first_hline_with_n_dark(im,n):
    """Find distance to vertical start of vop."""
    imwidth = im.size[0]
    imheight = im.size[1]
    row_dark_count = 0
    retval = 0
    search_backwards = False
    for y in range((imheight/2)-1):
        row_dark_count = 0
        for x in range(imwidth-1):
            try:
                pix_xy = im.getpixel((x,y))
                if pix_xy < 128:
                    row_dark_count = row_dark_count+1
                if row_dark_count > n:
                    retval = y
                    break
            except:
                pass
        if retval != 0:
            break
    if retval == 0:
            search_backwards = True
    if search_backwards:
        for y in range(imheight-1,(imheight/2) -1,-1):
            row_dark_count = 0
            for x in range(imwidth-1):
                try:
                    pix_xy = im.getpixel((x,y))
                    if pix_xy < 128:
                        row_dark_count = row_dark_count+1
                    if row_dark_count > n:
                        retval = y - 55 #nominal_height_of_vop 
                        break
                except:
                    ###pdb.set_trace()()
                    pass
            if retval != 0:
                break
    return retval

def cv2_first_vline_with_n_dark(im,n):
    """Find distance to horizontal start of vop."""
    imheight,imwidth = im.shape
    retval = -1
    search_backwards = False
    for x in range((imwidth/2) - 1):
        s0 = cv2.sumElems(cv2.bitwise_not(im[0:imheight-1,x:x+1]))
        s0 = s0[0]/255
        # this is a vops vertical line if thick enough; at 300 dpi, >8 pix
        # see if this line is still around four pixels later !!!dpi adj
        if s0 > n:
            s1 = cv2.sumElems(cv2.bitwise_not(im[0:imheight-1,x+4:x+5]))
            s1 = s1[0]/255
            if s1 > n:
                retval = x
                break
            # if not, see if this line was around two pixels earlier
            # and is still around 3 pixels later !!!dpi adj
            elif x > 1:
                s2 = cv2.sumElems(cv2.bitwise_not(im[0:imheight-1,x-2:x-1]))
                s2 = s2[0]/255
                s3 = cv2.sumElems(cv2.bitwise_not(im[0:imheight-1,x+3:x+4]))
                s3 = s3[0]/255
                if s2 > n and s3 > n:
                    retval=x
                    break
                

    if retval == -1:
        search_backwards = True
    if search_backwards:
        for x in range(imwidth-1,(imwidth/2)-1,-1):
            s2 = cv2.sumElems(cv2.bitwise_not(im[0:imheight-1,x:x+1]))
            s2 = s2[0]/255
            if s2 > n:
                retval = x - imwidth
                break
    return retval

def first_vline_with_n_dark(im,n):
    """Find distance to horiz start of voteop given more than half"""
    imwidth = im.size[0]
    imheight = im.size[1]
    col_dark_count = 0
    retval = 0
    search_backwards = False
    for x in range((imwidth/2) - 1):
        col_dark_count = 0
        for y in range(imheight-1):
            try:
                pix_xy = im.getpixel((x,y))
                if pix_xy < 128:
                    col_dark_count = col_dark_count+1
                if col_dark_count > n:
                    retval = x
                    break
            except:
                ###pdb.set_trace()()
                pass
        if retval != 0:
            break
    if retval == 0:
            search_backwards = True
    if search_backwards:
        for x in range(imwidth-1,(imwidth/2)-1,-1):
            col_dark_count = 0
            for y in range(imheight-1):
                try:
                    pix_xy = im.getpixel((x,y))
                    if pix_xy < 128:
                        col_dark_count = col_dark_count+1
                    if col_dark_count > n:
                        retval = x - 102 #nominal_width_of_vop
                        break
                except:
                    ###pdb.set_trace()()
                    pass
            if retval != 0:
                break
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
        ###pdb.set_trace()()
        pass
    try:
        if retval[-1]=='\n':
            retval = retval[:-1]
    except Exception as e:
        pass
    return retval


if __name__ == '__main__':
    template = cv2.imread('/home/mitch/vops/template.jpg')
    img = cv2.imread('/home/mitch/vops/vops_split/000001.jpg')
    print time.strftime("%Y-%m-%d %H:%M:%S")
    for n in range(1):
        minLoc,maxLoc = find_ulc(img[100:300,100:300],template)
    print time.strftime("%Y-%m-%d %H:%M:%S")
    pdb.set_trace()
    print minLoc,maxLoc
