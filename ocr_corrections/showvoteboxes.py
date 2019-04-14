
from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageOps
import collections
import datetime
from subprocess import call
import tempfile
from DetailLine.DetailLine import *


def outpagedim(inches):
    return int(inches * OUTPUT_PAGE_RES)  # Output page dimension in pixels.

def outcelldim(inches):
    return int(inches * OUTPUT_CELL_RES)  # Output cell dimension in pixels

def indim(inches):
    return int(inches * INPUT_RES)   # Input dimension in pixels

def rescale(factor, iterable):
    return [int(x * factor) for x in iterable]

def rescale_in_to_cell(iterable):
    return rescale(float(OUTPUT_CELL_RES) / INPUT_RES, iterable)

def scaledpx(x):
    """Given input-scale pixels x return the output-cell pixels."""

    return int(x * OUTPUT_CELL_RES / INPUT_RES) # resize input for output

# -------------------------------------------    Debugging

def p(image):
    """Display PIL image in Photoshop."""

    pth = tempfile.mkstemp('.png')[1]
    image.save(pth)
    call(('/usr/bin/open', '-a', '/Applications/Adobe Photoshop CC 2018/Adobe Photoshop CC 2018.app', pth))


# -------------------------------------------    PIL Box and Size

class Box(object):
    """Define a box where one can iterate through the points in a logical sequence.
    """
    def __init__(self, ulcx, ulcy, lrcx, lrcy):
        self.ulcx = ulcx
        self.ulcy = ulcy
        self.lrcx = lrcx
        self.lrcy = lrcy

    def __iter__(self):
        for attr in 'ulcx ulcy lrcx lrcy'.split(' '):
            yield self.__dict__[attr]

    def tup(self):
        return tuple(x for x in self)

    def size(self):
        """Return a Size for this box."""

        return Size(self.lrcx - self.ulcx, self.lrcy - self.ulcy)

    def __repr__(self):
        return '<Box: ulcx{}; ulcy:{}, lrcx{}; lrcy:{}>'\
               .format(self.ulcx, self.ulcy, self.lrcx, self.lrcy)


class Size(object):
    """width and height, iterable."""

    def __init__(self, width, height):
        self.width = width
        self.height = height

    def __iter__(self):
        for attr in 'width height'.split(' '):
            yield self.__dict__[attr]

    def tup(self):
        return tuple(x for x in self)

    def box(self, ulcx, ulcy):
        """Return a box of this size starting at the ULC."""

        return Box(ulcx, ulcy, self.width + ulcx, self.height + ulcy)

    def __repr__(self):
        return '<Size: width{}; height:{}>'.format(self.width, self.height)


# -------------------------------------------    PIL parameters and routines
#
font = ImageFont.truetype('/Library/Fonts/Arial.ttf', 16)
bigfont = ImageFont.truetype('/Library/Fonts/Arial.ttf', 48)
drawcolor = (0, 0, 255)
altcolor  = (255, 0, 0)

class Outpage(object):
    """Create and manage the output of pages -- image cells arranged left to right
       down the page."""

    def __init__(self, outputPDF, heading):
        self.margin = outpagedim(0.5)
        self.size = Size(outpagedim(8.5), outpagedim(11))
        self.nextx = self.margin
        self.nexty = self.margin
        self.rowheight = 0              # tallest cell seen so far on this row

        # slightly off white color to highlight the cells
        #
        self.bckgrnd_col = (224, 248, 224)
        self.pageimage = Image.new('RGB', (self.size.width, self.size.height),
                                   color=self.bckgrnd_col)
        self.imagedraw = ImageDraw.ImageDraw(self.pageimage)
        self.pad = outcelldim(0.2)
        self.outputPDF = outputPDF
        with open(outputPDF,'w') as ouf:        # create an empty output file
            pass
        self.pagenum = 0
        self.heading = heading + ':  ' + str(datetime.date.today())

    def add(self, cell_image):
        '''Add the input image as a cell. The image is already scaled to the outpur resolution.'''

        (x, y) = cell_image.size
        sourcedraw = ImageDraw.ImageDraw(cell_image)     # naughty -- draws on the input
        sourcedraw.rectangle((0, 0, x-1, y -1), outline=drawcolor)
        endx = self.nextx + x + self.pad
        if endx + self.margin > self.size.width:     # will this cell fit in this row?
            self.nextx = self.margin            # no, start a new row
            self.nexty += self.rowheight + self.pad
            self.rowheight = 0
            if self.nexty + y > self.size.height - self.margin: # did the prior row fill up the page?
                self.output_page()                              # yes, output start a new one
                self.nexty = self.margin

        self.pageimage.paste(cell_image, (self.nextx, self.nexty,
                                          self.nextx + x, self.nexty + y))
        self.nextx += x + self.pad
        self.rowheight = max(self.rowheight, y + self.pad)

    def text_cell(self, text, font, margin=0.25, color = (0,0,0)):
        """Create a cell in the page with the input text."""

        sizetxt = self.multiline_text_size(text, font)
        scaledmargin = outcelldim(margin)
        sizebox = Size(*[s + 2 * scaledmargin for s in sizetxt])
        cell = Image.new('RGB',tuple(sizebox), color = (255, 255,255))
        celldraw = ImageDraw.ImageDraw(cell)
        celldraw.text([scaledmargin, scaledmargin], text, font=font, fill=color)
        return cell

    def multiline_text_size(self, text, font):
        '''Return the extended sizes for a multiline box of text.'''

        w=0
        h=0
        for line in text.split('\n'):
            (tw, th) = font.getsize(line)
            w = max(w, tw)
            h += font.size + 2

        return Size(w, h)

    def output_page(self):
        self.pagenum += 1
        print "page {} out".format(self.pagenum)
        self.imagedraw.text((self.margin, int(self.margin/2), self.margin+500, self.margin),
                            self.heading + ', page ' + str(self.pagenum), font=font, fill=(0,0,0))
        self.pageimage.save(self.outputPDF, 'PDF', append=True, resolution=OUTPUT_PAGE_RES)
        self.imagedraw.rectangle((0, 0, self.pageimage.size[0], self.pageimage.size[1]),
                                 fill=self.bckgrnd_col)


def thickrect(draw, xy, linewid, color):
    """Draw a rectange of linewid thickness. Shift if outside target on left."""

    (ulcx, ulcy, lrcx, lrcy) = (x for x in xy)
    start = 0 #int(linewid / 2)
    end = linewid - 1
    if ulcx < linewid:
        adjust = linewid - ulcx
        ulcx += adjust
        lrcx += adjust
    while start <= end:
        rect =(ulcx - start, ulcy - start, lrcx + start, lrcy + start)
        draw.rectangle(rect, outline=color)
        start += 1

# ----------------------------------------------   Access to Details_fuzzy
#

def retrieve_dls(filter_func):
    """Returns a list of rows selected by filter_func returning true."""
    with open(DETAILS_FUZZY) as inf:
        list = []
        for line in inf:
            dl = Detail_line(line)
            if filter_func(dl):
                list.append(dl)
    return list

# ----------------------------------------------   Create the output cell for one ballot
#
IMG_PATH_PFX = '/Users/Wes/NotForTheCloud/2018_June/unproc'
# oldIMG_PATH_PFX = '/media/psf/Home/NotForTheCloud/2018_June/unproc'
DETAILS_FUZZY = '../output/details_fuzzy.csv'

def showvotes(voteops):
    """Create an image of the image marks from a ballot correlating info from
     the voteops, all from the same ballotimage and contest."""

    invotemarkbox = get_invotemarkbox(voteops)
    outroomforimprintpx = outcelldim(0.4)     # Add this much on bottom for imprint.
    outroomfortextpx   = outcelldim(0.2)     # Add for file number.

    # Gather input image size + allowances for other info,
    # compute the size of the output cell, and create it.
    #
    w, h = invotemarkbox.size()
    outimgsizepx = Size(*[scaledpx(x) for x in (w, h)])
    outimgsizepx.height += outroomforimprintpx + outroomfortextpx
    outcell = Image.new('RGB', outimgsizepx.tup(), (255, 255, 255))
    outcelldraw = ImageDraw.ImageDraw(outcell)

    inputimage, frontpage, imagenum = get_images(voteops)
    inballotmarks = inputimage.crop(invotemarkbox)

    # Resize input image and paste in output cell.
    #
    outballotmarks = inballotmarks.resize((rescale_in_to_cell(inballotmarks.size)),
                                          Image.BICUBIC)
    outcell.paste(outballotmarks)

    # Grab the printed precinct_id from the ballot and place it in the
    # ULC of the cell.
    #
    precinctin = inputimage.crop(precinct_loc_in)
    precinctout = precinctin.resize(rescale(float(OUTPUT_CELL_RES) / INPUT_RES,
                                            precinct_loc_in.size()),
                                    Image.BICUBIC)

    outcell.paste(precinctout, (0,0))
    outcelldraw.rectangle((0, 0, precinctout.width - 1, precinctout.height - 1), outline=(0,0,255))

    # Grab the imprint, enhance it, and place it below the image marks.
    #
    imprint = frontpage.crop(imprint_loc_in).transpose(Image.ROTATE_90)
    impscale = min(float(outcell.width) / imprint.width, float(OUTPUT_CELL_RES) / INPUT_RES)
    imprint = imprint.resize(rescale(impscale, (imprint.width, imprint.height)),
                             Image.BICUBIC)
    contrast = ImageEnhance.Contrast(imprint)
    imprint = contrast.enhance(12.0)
    blur = ImageEnhance.Sharpness(imprint)
    imprint = blur.enhance(0.25)
    imp_ulcx = 0
    imp_ulcy = outcell.height - outroomforimprintpx - outroomfortextpx
    outcell.paste(imprint, (imp_ulcx, imp_ulcy))

    # Print the image number below the imprint.
    #
    (w, h) = font.getsize(imagenum)     # adjust ulc to center text
    center = outcell.width / 2
    imgnum_ulcx = int(center - w / 2)
    imgnum_ulcy = outcell.height - outroomfortextpx

    outcelldraw.text((imgnum_ulcx, imgnum_ulcy), imagenum,
                     font=font, fill=drawcolor)

    # base.save('/Users/Wes/Downloads/base.jpg')

    # Draw rectangles over the mark areas on the output image.
    #
    for vo in voteops:
        mark_ulcx = scaledpx(vo['adjusted_x'] - invotemarkbox.ulcx)
        mark_ulcy = scaledpx(vo['adjusted_y'] - invotemarkbox.ulcy)
        mark_lrcx = mark_ulcx + output_mark_sizepx.width
        mark_lrcy = mark_ulcy + output_mark_sizepx.height
        thickrect(outcelldraw, (mark_ulcx, mark_ulcy, mark_lrcx, mark_lrcy),
                  4, drawcolor)
        if vo['was_voted']:
            mark_lrcx += outcelldim(COL_WIDTH) / 2  #shift the X towards the center of the column

            mark_height_adj = int(0.18 * bigfont.getsize('X')[1])    # allow for blank space at top of letters
            xloc = (mark_lrcx, mark_ulcy - mark_height_adj)
            outcelldraw.text(xloc, 'X', font=bigfont, fill=altcolor)
    op.add(outcell)

def get_invotemarkbox(voteops):
    """Construct a box that describes the input vote marking areas
       for this contest."""

    col_widthpx = indim(COL_WIDTH)
    szvo = len(voteops)
    ulcx = min([voteops[k]['adjusted_x'] for k in range(0, szvo)])
    ulcy = min([voteops[k]['adjusted_y'] for k in range(0, szvo)])
    lrcx = max([voteops[k]['adjusted_x'] for k in range(0, szvo)])
    lrcy = max([voteops[k]['adjusted_y'] for k in range(0, szvo)])

    # Adjust right side of box to encompass whole columns.
    #
    w = lrcx - ulcx
    wcols = int((w - 1) / col_widthpx) + 1
    lrcx = ulcx + wcols * col_widthpx

    # Add some room on the bottom because the bottom of the vote box
    # is not hte bottom of that item on the ballot.
    #
    lrcy += indim(MARK_SIZE.height + 0.25)
    return Box(ulcx, ulcy, lrcx, lrcy)

def get_images(voteops):
    """Return the input image and the image where the imprint is,
       which may be a pointer to the input image."""

    imgpath = IMG_PATH_PFX + voteops[0]['file1'][len(oldIMG_PATH_PFX):]
    inputimage = Image.open(imgpath).convert('RGB')
    imagenum = imgpath[-10:-4]
    lastdigit = int(imgpath[-5 : -4])
    if lastdigit % 2:
        frontpage = Image.open(imgpath[:-5] + str(lastdigit - 1) +  imgpath[-4:])
    else:
        frontpage = inputimage
    return inputimage, frontpage, imagenum

def countvotes(voteops, votecounters):
    """Update the votoecounters from the voteops. Return abnormal boolean."""

    abnormal = False
    for contest in votecounters.keys():
        votes = [v.fuz_choice for v in voteops if v.initial_voted == '1' and v.fuz_contest == contest]
        if len(votes) == 0:
            votes.append('(no vote)')
            abnormal = True
        if len(votes) > 1:
            votes =['multivote']
            abnormal = True
        votecounters[contest].update(votes)
        # abnormal = v.file == '/media/psf/Home/NotForTheCloud/2018_June/unproc/020/020646.jpg'

    return abnormal


#  -------------------------------   MAIN     -------------------------------

IMG_PATH_PFX = '/Users/Wes/NotForTheCloud/2018_Nov/unproc'

INPUT_RES =  300         # all input images are from 300 dpi ballots
OUTPUT_PAGE_RES = 150    # PDF page is an image of this res
INPUT_RES =  300         # all input images are from 300 dpi ballots
OUTPUT_CELL_RES = 100     # each cell in the output page is an image of this res

# Ballot-specific parameters
#
IMPRINT_LOC = Box(0.1, 6.43, 0.47, 8.233)
PRECINCT_LOC = Box(5.5, 1.333, 6.667, 1.667)
BALLOTSIZE = Size(8.5, 14)
BALLOT_SIZE_INPUT_RES = Size(*[indim(x) for x in BALLOTSIZE])
MARK_SIZE = Size(0.333, 0.18)
COL_WIDTH = 2.4         # column width in inches

output_mark_sizepx = Size(*[int(float(_) * OUTPUT_CELL_RES) \
                            for _ in MARK_SIZE])
precinct_loc_in = Box(*rescale(float(INPUT_RES), PRECINCT_LOC))   # inches to output res
imprint_loc_in = Box(*(indim(_) for _ in IMPRINT_LOC))

op = Outpage('/Users/Wes/Downloads/%TU--1Gov.pdf',
             '5TU--1 on Governor')
xspan = 150
yspan = 50


contests = ('GOVERNOR',)
votecounters = {c: collections.Counter() for c in contests}
voteops = retrieve_dls(lambda dl: \
            dl.pctid == '5T--1' and dl.fuz_contest == 'GOVERNOR' and dl.initial_voted == '1')

ballotcount = 0
numtoshow = 1000
numshowing = 0
currentBallot = None

i = 0
while i < len(voteops):
    j = i + 1

    # gather the voteops from this physical ballot and contest
    #
    while j < len(voteops) and voteops[i].file == voteops[j].file:
        j += 1

    print i, j, voteops[i].file
    abnormal = countvotes(voteops[i:j], votecounters)
    ballotcount += 1
    print votecounters


    # add the abstract of this ballot/contest to an output page
    #
    if abnormal: showvotes(voteops[i:j])
    i = j
    numshowing += 1
    # if i >240 : break

    # if numshowing % numtoshow == 0:
    #     x = raw_input('next {} of {}: '.format(numtoshow, len(voteops) - numshowing))

print votecounters
print ballotcount

# Create an textual summary to go on the last output page.
#
s = 'Ballot Count: {}\n\n'.format(ballotcount)

for c in sorted(votecounters.keys()):

    s1 = ''
    tot = 0
    for k in votecounters[c]:
        count = votecounters[c][k]
        tot += count
        s1 += '    {}:{:6d}\n'.format(k, count)

    s += '\n{}:  {}\n'.format(c, tot)
    s += s1

op.add(op.text_cell(s, font))
op.output_page()