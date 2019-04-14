
"""tally_pages_by_pct/tally_pages_by_pct.py

    Scan a tree of Hart ballots extracting the barcodes and reporting the number
    of pages by precinct.

    Barcode interpretation is farmed out to subprocesses to increase speed.

    The only command-line param is --num, number of subprocesses, (default
    number of processors on the computer).

    There are other options set in the opts dictionary at the start of main.

    This does not rely on or contribute to the VOPS module associated with TEVS
    and the Humboldt Election Transparancy Project (HETP). Nonetheless is is used
    in support of HETP and the code is housed in directories associated with VOPS.

"""


import argparse
import csv
import logging
import multiprocessing
from myLogging import myLogging
import os
from pyzbar.pyzbar import decode
from PIL import Image
import time



#  -----------------   Bar-code processing daemon  -----------------

def bar_code_daemon(file_list, next_item, outfile, pctids):
    """Process barcodes from selected files in source.

    file_list  - list of paths to image files
    outpath    - write the accumulated totals to this path altered by 'num'
    pctids     - dict to translate barcode excerpt to precinct ID"""

    def processfile(infile):
        """Extract barcode from an image and return the corresponding (pct_id, side_num)
           or (None, None)"""

        def good_barcode(barcode_list):
            """Return the (only valid barcode, page_num) in the list or
               raise an Exception."""

            if len(barcode_list) == 0:
                raise ValueError(infile + ' no barcodes found')

            good_barcodes = list()
            pct_id = None
            for barcode in barcode_list:
                if barcode.rect.width * barcode.rect.width == 0:
                    continue
                barcode_value = barcode.data
                if len(barcode_value) != 14:
                    continue

                if barcode_value[0] not in ('1', '2'):
                    continue

                barcode_page_num =  barcode_value[7:9]
                if barcode_page_num not in ('01', '02', '03', '04'):
                    continue

                try:
                    pct_id = pctids[barcode.data[1:8]]
                except KeyError as e:
                    continue

                good_barcodes.append(barcode)

            if len(good_barcodes) == 0:
                raise ValueError(infile + ' no valid barcodes found')

            if len(good_barcodes)> 1:

                # sometimes we see the same barcode value more than once. If this
                # is the only value it's ok to return.
                #
                out_bar_code = good_barcodes[0]
                for bc in good_barcodes[1:]:
                    if out_bar_code:
                        if bc.data != out_bar_code:
                            raise ValueError(infile + ' multiple different valid barcodes found')

            return (pct_id, int(barcode_page_num))

        # processfile(infile) starts here
        #
        crop_to = (0, 150, 126, 910)
        img = Image.open(infile)
        imgc = img.crop(crop_to)
        barcode_list = decode(imgc)


        # check for exactly one barcode that passes valididity checks
        #
        try:
            pct_id, page_num = good_barcode(barcode_list)
        except:

            # try the image upside down
            #
            imgc = img.transpose(Image.ROTATE_180).crop(crop_to)
            barcode_list = decode(img)
            pct_id, page_num = good_barcode(barcode_list)

        return pct_id, page_num    # end of processfile()


    # code starts here for: bar_code_daemon(file_list, next_item, outfile, pctids)
    #
    logging.info('Entering')
    rpt_dict = dict()
    processed = 0
    while True:
        with next_item.get_lock():
            if len(file_list) <= next_item.value:
                break

            fpath = file_list[next_item.value]
            next_item.value += 1

        pct_id, page_num = processfile(fpath)
        tot_list = rpt_dict.get(pct_id, [0, 0, 0, 0])
        tot_list[page_num - 1] += 1
        rpt_dict[pct_id] = tot_list
        processed += 1
        if processed % OPTS.log_interval == 0:
            logging.info('num processed={}; last processed={}'.format(processed,
                                                        os.path.basename(fpath)))

    logging.info('writing output')
    fmt = '{}\t{}\n'
    f = '{}'
    with open(outfile, 'w') as rptout:
        rptout.write('Precinct\tPage 1\tPage 2\tPage 3\tPage 4\t Total Pages\n')

        for pct_id in sorted(rpt_dict.keys()):
            row = rpt_dict[pct_id]
            t = '\t'.join((str(x)) for x in row)
            rptout.write(fmt.format(pct_id, t))


    logging.info('Processed {} files.'.format(processed))

def list_image_files(source_path, num, lowest, highest, shortrun):
    """Return a sorted list of paths to valid jpgs for images"""

    outl = list()
    cnt = 0
    for dirpath, dirnames, filenames in os.walk(source_path):
        for filename in filenames:
            cnt += 1
            fname_base = filename[0:6]
            if not fname_base.isdigit():
                continue

            fnum = int(fname_base)
            if lowest and fnum < lowest:
                continue

            if highest and fnum > highest:
                continue

            if '.jpg' == filename[-4:].lower():
                fpath = os.path.join(dirpath, filename)
                outl.append(fpath)

            if shortrun and sum([len(x) for x in outl]) >= shortrun:
                break

        if shortrun and len(outl) >= shortrun:
            break

    return sorted(outl)

def load_pct_ids(source):
    pctids = dict()
    with open(source) as pctfile:
        for line in pctfile:
            barcodefield, pct_id = line.split('\t')
            pct_id = pct_id.strip()
            pctids[barcodefield] = pct_id

    return pctids

# --------------------  Command Line Parameters  -------------------

def cmd_line_opts():
    parser = argparse.ArgumentParser(description=
                        "Scan image files to enerate tsv data for reporting counts by " +\
                        "precinct and page numbers.",)

    parser.add_argument('--num', default=multiprocessing.cpu_count(), type=int,
                        help='How many parallel processes.')

    return parser.parse_args()


# ===================================  MAIN  ===================================

if __name__ == '__main__':
    OPTS = cmd_line_opts()
    OPTS.base = '/Users/Wes/NotForTheCloud/2018_Nov/unproc/'
    OPTS.highest = 299999
    OPTS.log_interval = 250
    OPTS.lowest = 0
    fname_mod = '' if OPTS.num is None else str(OPTS.num)
    OPTS.out_template = '/Users/Wes/Dropbox/Programming/ElectionTransparency/vops_addons/output/1811_by_pct#.tsv'
    OPTS.pctsource = '/Users/Wes/Dropbox/Programming/ElectionTransparency/vops_addons/data/static_2018_nov/from_elections/precincts_massaged.txt'
    OPTS.shortrun = None
    OPTS.theseonly = None
    myLogging.basicConfig(name=os.path.basename(__file__))
    logging.info("NUMOPT: {}".format(OPTS.num))
    bcodes = set()
    totcnt = 0
    overall_start = time.time()
    errors = []

    pctids = load_pct_ids(OPTS.pctsource)
    if OPTS.theseonly:
        file_list = [OPTS.theseonly]
    else:
        file_list = list_image_files(OPTS.base, OPTS.num, OPTS.lowest,
                                        OPTS.highest, OPTS.shortrun)

    logging.info('Files to process: {}'.format(len(file_list)))
    next_item = multiprocessing.Value('l')
    next_item.value = 0

    # run parallel processes extracting barcodes from files
    #
    subprocesses = list()
    worker_output_files = list()
    for worker_num in range(multiprocessing.cpu_count()):
        outp = OPTS.out_template.replace('#', str(worker_num))
        worker_output_files.append(outp)
        args = (file_list, next_item, outp, pctids)
        subprocesses.append(multiprocessing.Process(target=bar_code_daemon, args=args))
        subprocesses[-1].start()
    for subp in subprocesses:
        subp.join()

    logging.info('Subprocesses complete.')

    # Read in and consolidate the outputs from the parallel processes.
    #
    rpt_dict = dict()  # key = pcd_id, value [counts for pages 1-4]

    for file in worker_output_files:
        with open(file) as inf:
            _ = inf.readline()  # header
            csvreader = csv.reader(inf, delimiter='\t')
            for row in csvreader:
                pct_id = row[0]
                tot_list = rpt_dict.get(pct_id, [0, 0, 0, 0])
                for i in range(1, 5):
                    tot_list[i - 1] += int(row[i])

                rpt_dict[pct_id] = tot_list

    # Write consolidated report
    #
    logging.info('writing consolidated data')
    ofp = OPTS.out_template.replace('#', '')
    totals = [0, 0, 0, 0]
    with open(ofp, 'w') as rptout:
        rptout.write('Precinct\tPage 1\tPage 2\tPage 3\tPage 4\t Total Pages\n')
        rptw = csv.writer(rptout, delimiter='\t')
        for pct_id in sorted(rpt_dict.keys()):
            x = rpt_dict[pct_id]
            row = ['~ ' + pct_id] +  x + [sum(x)]   # '~' is a hack so Excel doesn't see
                                                    # 1E-46 as a floating point umber
            rptw.writerow(row)
            for i in range(len(totals)):
                totals[i] += row[i + 1]

        rptw.writerow(['Totals'] + totals + [sum(totals)])

    for file in worker_output_files:
        os.remove(file)

