import argparse
import pdb
import sys
import tempfile
def parse_command_line():
    parser = argparse.ArgumentParser(
        description='Process Hart-style ballot images.'
    )
    parser.add_argument('-dpi','--dpi',
                        help="Resolution of images, in dots per inch",
                        type=int,
                        default = 300
    )
    parser.add_argument('-box','--box-dark-pixel-min',
                        help="Minimum dark pixel count to establish vote op box.",
                        type=int,
                        default = 2400 # Hart, 300 dpi
    )
    parser.add_argument('-cov','--coverage-threshold',
                        help="Minimum dark pixel count to establish vote.",
                        type=int,
                        default = 3500 # Hart, 300 dpi
    )
    parser.add_argument('-dark','--darkness-threshold',
                        help="Minimum intensity for pixel to be considered dark.",
                        type=int,
                        default = 192 # in range 0..255
    )
    parser.add_argument('-slow','--slow-ok',action='store_true',
                        help="It is acceptable to capture more information, slowing results."
    )
    parser.add_argument('-bc','--barcode-only',action='store_true',
                        help="Quickly examine and report barcodes to barcodes.csv."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-odd',action='store_true',
                        help="Process only odd numbered images"
    )
    group.add_argument('-even',action='store_true',
                        help="Process only even numbered images"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-left','--votes-left-of-text',action='store_const',
                       dest = 'vote_loc',const='l',
                        help="Vote marks to left of text"
    )
    group.add_argument('-right','--votes-right-of-text',action='store_const',
                       dest = 'vote_loc',const='r',
                       help="Vote marks to right of text"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-pathspec','--pathspec',
                        help="Path to images, following glob rules; e.g.: /media/*/*jpg will load all files in folders one underneath /media with names ending in jpg. Cannot be used if filelist is provided."
    )
    group.add_argument('-filelist','--filelist',
                        help="Name of a file containing a list of image files to process. Cannot be used if pathspec is provided."
    )
    parser.add_argument('-logfile','--log-file',
                        help = 'Path to file where logging data is written.',
                        default = 'vops_log.log'
    )
    parser.add_argument('-logint','--log-level-int',
                        help = 'Log level for python logging module, as integer.',
                        type=int,
                        default = 30
    )
    parser.add_argument('-coffs','--column-offsets',
                        help='Comma separated list of vop x offsets, as percent of dpi',
                        default='7,250,493'
    )
    parser.add_argument('-ptr','--precinct-text-region-xywh',
                        help='Comma separated list of (x,y,w,h) specifying location of precinct id text, as percent of dpi, relative to ulc; negatives allowed',
                        default='433,67,200,20'
    )
    parser.add_argument('-btr','--barcode-region-xywh',
                        help='Comma separated list of (x,y,w,h) specifying location of categorizing barcode, as percent of dpi, relative to ulc; negatives allowed',
                        default='-30,-3,22,253'
    )
    parser.add_argument('-ulsr','--ulc-search-region-xywh',
                        help='Comma separated list of (x,y,w,h) specifying location to search for image upper left corner, as percent of dpi. Enlarging this region slows things down and may introduce problems, so keep it as tight as you can.',
                        default='35,58,56,45'
    )
    parser.add_argument('-ursr','--urc-search-region-xywh',
                        help='Comma separated list of (x,y,w,h) specifying location to search for image upper left corner, as percent of dpi. Enlarging this region slows things down and may introduce problems, so keep it as tight as you can.',
                        default='749,63,84,37'
    )
    parser.add_argument('-minw','--minimum-width-of-vop',
                        help='Minimum width of identifiable voting box/oval, as percent of dpi',
                        type=int,
                        default=33
    )
    parser.add_argument('-maxw','--maximum-width-of-vop',
                        help='Maximum width of identifiable voting box/oval, as percent of dpi',
                        type=int,
                        default=50
    )
    parser.add_argument('-width','--nominal-width-of-vop',
                        help='Nominal width of identifiable voting box/oval, as percent of dpi',
                        type=int,
                        default=34
    )
    parser.add_argument('-height','--nominal-height-of-vop',
                        help='Nominal height of identifiable voting box/oval, as percent of dpi',
                        type=int,
                        default=18
    )
    parser.add_argument('-minh','--minimum-height-of-vop',
                        help='Minimum height of identifiable voting box/oval, as percent of dpi',
                        type=int,
                        default=17
    )
    parser.add_argument('-maxh','--maximum-height-of-vop',
                        help='Maximum height of identifiable voting box/oval as percent of dpi',
                        type=int,
                        default=24
    )
    parser.add_argument('-miny','--minimum-y-of-vop',
                        help='Minimum y offset of vop as percent of dpi',
                        type=int,
                        default = 90
    )
    parser.add_argument('-maxy','--maximum-y-of-vop',
                        help='Maximum y offset of vop as percent of dpi',
                        type=int,
                        default = 1333
    )
    parser.add_argument('-minx','--minimum-x-of-vop',
                        help='Minimum x offset of vop as percent of dpi',
                        type=int,
                        default = 45
    )
    parser.add_argument('-maxx','--maximum-x-of-vop',
                        help='Maximum x offset of vop as percent of dpi',
                        type=int,
                        default = 800
    )
    parser.add_argument('-colw','--column-width',
                        help = 'Column width as percent of dpi',
                        type = int,
                        default = 233
    )
    parser.add_argument('-colm','--column-margin',
                        help = 'Column edge to vote box edge as percent of dpi',
                        type = int,
                        default = 10
    )
    parser.add_argument('-leftm','--left-margin',
                        help = 'Left image edge to enclosing box edge as percent of dpi',
                        type = int,
                        default = 60
    )
    parser.add_argument('-rightm','--right-margin',
                        help = 'Right image edge to enclosing box edge as percent of dpi',
                        type = int,
                        default = 60
    )
    parser.add_argument('-vslack','--vop-slack',
                        help='When a vote op is located only during reconciliation, this is the number of pixels by which to expand the cropping region to capture the voteop\'s dark pixel count.',
                        type=int,
                        default=4
    )
    parser.add_argument('-ss','--sort-stride',
                        help='To assist the 2D sort, specify a value whose multiples will not be near column edges. For example, if columns begin one inch in and are 2 inches wide, use 200 (percent) to split the sort at the center of columns. ',
                        type=int,
                        default=200
    )
    parser.add_argument('-tmp','--temp-dir',
                        help='Location at which to place temp files. ',
                        default=tempfile.mkdtemp(prefix='tevs')
    )
    
    args = parser.parse_args()
            
    # make dpi a global
    print "DPI must be 300 to work with current embedded upper left corner image"
    dpi = args.dpi
    if dpi != 300:
        sys.exit(0)
    # widths, heights, stride
    # are provided as hundredths of inch,
    # so convert to pixels
    try:
        args.sort_stride = (args.dpi*args.sort_stride)/100
    except:
        pass
    try:
        args.column_offsets = [((int(s)*args.dpi)/100) for s in args.column_offsets.split(',')]
    except:
        pass
    try:
        args.precinct_text_region_xywh = [((int(s)*args.dpi)/100) for s in args.precinct_text_region_xywh.split(',')]
    except:
        pass
    try:
        args.barcode_region_xywh = [((int(s)*args.dpi)/100) for s in args.barcode_region_xywh.split(',')]
    except:
        pass
    try:
        args.ulc_search_region_xywh = [((int(s)*args.dpi)/100) for s in args.ulc_search_region_xywh.split(',')]
    except:
        pass
    try:
        args.urc_search_region_xywh = [((int(s)*args.dpi)/100) for s in args.urc_search_region_xywh.split(',')]
    except:
        pass
    try:
        args.minimum_width_of_vop = (args.dpi*args.minimum_width_of_vop)/100
    except:
        pass
    try:
        args.maximum_width_of_vop = (args.dpi*args.maximum_width_of_vop)/100
    except:
        pass
    try:
        args.nominal_width_of_vop = (args.dpi*args.nominal_width_of_vop)/100
    except:
        pass
    try:
        args.minimum_height_of_vop = (args.dpi*args.minimum_height_of_vop)/100
    except:
        pass
    try:
        args.maximum_height_of_vop = (args.dpi*args.maximum_height_of_vop)/100
    except:
        pass
    try:
        args.nominal_height_of_vop = (args.dpi*args.nominal_height_of_vop)/100
    except:
        pass
    try:
        args.minimum_y_of_vop = (args.dpi*args.minimum_y_of_vop)/100
    except:
        pass
    try:
        args.maximum_y_of_vop = (args.dpi*args.maximum_y_of_vop)/100
    except:
        pass
    try:
        args.minimum_x_of_vop = (args.dpi*args.minimum_x_of_vop)/100
    except:
        pass
    try:
        args.maximum_x_of_vop = (args.dpi*args.maximum_x_of_vop)/100
    except:
        pass
    try:
        args.column_width = (args.dpi*args.column_width)/100
    except:
        pass
    try:
        args.column_margin = (args.dpi*args.column_margin)/100
    except:
        pass
    try:
        args.left_margin = (args.dpi*args.left_margin)/100
    except:
        pass
    try:
        args.right_margin = (args.dpi*args.right_margin)/100
    except:
        pass
    
    # default is for vote_loc to left of text
    try:
        if not args.vote_loc:
            args.vote_loc='l'
        elif args.vote_loc=='l':
            pass
        elif args.vote_loc == 'r':
            pass
    except:
        args.vote_loc = 'l'
    return args

if __name__ == '__main__':
    args = parse_command_line()
    print args
