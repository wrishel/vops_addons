
"""
Read args.DETAILS_IN, which is normally the sorted output of tevs_matcher_v2.py.

For example, at main in this program there is a statement that might read like

The output of tevs_matcher_v2.py must be sorted by these keys (major to minor)

    file
    corrected_barcode
    fuz_choice     (TODO: why is this here; it seems irrelevant)
    fuz_contest


Reset voted and overvoted fields based on threshold number of darkened pixels
per voting box (command line arg), text of contests, and the allowed number of votes f
or a ballot in the specific contest which is determined by parsing the fuz_contest field.
For each contest and choice report contest, choice, vote ops, and votes,
excluding overvotes.

Write output to args.DETAILS_OUT

See data for testing details.csv at bottom of source, and intended results.
"""
import argparse
import csv
from DetailLine.DetailLine import *

import os

def write_rowstack(rs):
    with open(args.DETAILS_OUT,'a') as output_file:
        csv_writer = csv.writer(output_file, lineterminator=u'\n') # default adds carriage return,
                                                                   # which screws up grep '$' in pattern
        for r in rs:
            csv_writer.writerow(r.aslist())


def set_rowstack_over_under(rs, thresh = 4200, allowed=1):
    '''Process all the votes for a contest within a precinct; identify over- and under-votes.
       Also recalculate 'was_voted using parameters different from those used in vops.

       If there are overvotes, set the actual votes to 0 and record the total overvotes
       in the row for each choice.

       If there are undervotes, leave the actual votes as computed but record the number of
       overvotes in the row for each choice.'''

    # Deternmine allowed votes from fuz_contest of the first row in the stack.
    #
    if 'THAN TWO' in rs[0].fuz_contest:
        allowed = 2
    elif 'THAN 2' in rs[0].fuz_contest:
        allowed = 2
    elif 'THAN THREE' in rs[0].fuz_contest:
        allowed = 3
    elif 'THAN 3' in rs[0].fuz_contest:
        allowed = 3

    # reset initial_voted for darkened pixels >= thresh or <= 90% of thresh
    #
    for r in rs:
        # print r.initial_voted, int(r.darkened_px_cnt), thresh, (9*thresh)/10

        # change initial-voted value based on thresholds different than used in vops
        #
        if int(r.darkened_px_cnt) >= thresh:
            if r.initial_voted == 0: print 'reset to one for {}'.format(r.fuz_choice)
            r.initial_voted = '1'
        elif int(r.darkened_px_cnt) < (9*thresh)/10:
            if r.initial_voted == 1: print 'reset to 0 for {}'.format(r.fuz_choice)
            r.initial_voted  = '0'

    ballots = dict()    # collect voteops by file name
    for r in rs:
        ballot_set = ballots.get(r.file, set())
        ballot_set.add(r)
        ballots[r.file] = ballot_set

    for  ballotset in ballots.values():
        vote_count = 0
        for ballot in ballotset:
            vote_count += int(ballot.initial_voted)

        if vote_count > allowed:  # if we are overvoted
            for ballot in ballotset:
                ballot.initial_overvoted = vote_count
                ballot.initial_voted = 0
                ballot.undervoted = 0

        elif vote_count < allowed: # if we are undervoted
            for ballot in ballotset:
                ballot.initial_overvoted = 0
                ballot.undervoted = allowed - vote_count

        else:                   # if we are just right
            for ballot in ballotset:
                ballot.initial_overvoted = 0
                ballot.undervoted = 0

    return
            

def parse_command_line():
    parser = argparse.ArgumentParser(
        description='Determine overvotes in a file with details.csv format.'
    )
    parser.add_argument('-t','--threshold',
                        help="Dark pixel threshold for substantial mark",
                        type=int,
                        default = 4000
    )
    return parser.parse_args()


if __name__ == "__main__":
    rowstack = []
    current_contest = None
    current_votes = 0
    args = parse_command_line()
    pth_big_files = '/Users/Wes/NotForTheCloud/2018_Nov/in-process'
    args.DETAILS_IN =  os.path.join(pth_big_files, 'details_fuzzy_sorted16.csv')
    args.DETAILS_OUT = os.path.join(pth_big_files, 'details_fuzzy_overv16.csv')
    threshold = args.threshold
    print "Command line args",args
    open(args.DETAILS_OUT, 'w').close()   # initialize output file
    lcnt = 0
    SHORT_RUN = None            # for debugging, read only this many input lines
    PROCESS_ONLY = set([        # for debugging, process only these files
        # '018701.jpg',
    ])
    with open(args.DETAILS_IN,'r') as details_file:
        csv_reader = csv.reader(details_file, delimiter=',')
        for row in csv_reader:
            dl = Detail_line(row)
            if lcnt % 100000 == 0:
                print lcnt
            lcnt += 1
            if len(PROCESS_ONLY) > 0 and dl.file not in PROCESS_ONLY:
                continue

            if dl.fuz_contest != current_contest:
                if len(rowstack) > 0:
                    set_rowstack_over_under(rowstack, threshold)
                    write_rowstack(rowstack)
                    rowstack = []
                    current_votes = 0
            rowstack.append(dl)
            current_contest = dl.fuz_contest
            if SHORT_RUN and lcnt >= SHORT_RUN:
                break

    # empty rowstack at EOF
    print lcnt

    if len(rowstack) > 0:
        set_rowstack_over_under(rowstack,threshold)
        write_rowstack(rowstack)

"""
<<< These may no longer be correct. They are certianly not complete, since
we have added undervote tracking.>>>
TEST (write csv lines below to details.csv, should get output as below)
0,1,2.jpg are repeated with different ordering as 10,11,12
000000.jpg,20000900400046,ONEVOTE VOTE FOR ONE,APPLE,1,5000,1,2,3,4,0,0
000000.jpg,20000900400046,ONEVOTE VOTE FOR ONE,BANANA,1,5000,1,2,3,4,0,0
000000.jpg,20000900400046,ONEVOTE VOTE FOR ONE,PEACH,1,5000,1,2,3,4,0,0
000000.jpg,20000900400046,ONEVOTE VOTE FOR ONE,PEAR,0,2500,1,2,3,4,0,0
000000.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,APPLE,1,5000,1,2,3,4,0,0
000000.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,BANANA,1,5000,1,2,3,4,0,0
000000.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,PEACH,1,5000,1,2,3,4,0,0
000000.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,PEAR,0,2500,1,2,3,4,0,0
000000.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,APPLE,1,5000,1,2,3,4,0,0
000000.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,BANANA,1,5000,1,2,3,4,0,0
000000.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,PEACH,1,5000,1,2,3,4,0,0
000000.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,PEAR,0,2500,1,2,3,4,0,0
000001.jpg,20000900400046,ONEVOTE VOTE FOR ONE,APPLE,1,5000,1,2,3,4,0,0
000001.jpg,20000900400046,ONEVOTE VOTE FOR ONE,BANANA,1,5000,1,2,3,4,0,0
000001.jpg,20000900400046,ONEVOTE VOTE FOR ONE,PEACH,0,2500,1,2,3,4,0,0
000001.jpg,20000900400046,ONEVOTE VOTE FOR ONE,PEAR,0,2500,1,2,3,4,0,0
000001.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,APPLE,1,5000,1,2,3,4,0,0
000001.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,BANANA,1,5000,1,2,3,4,0,0
000001.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,PEACH,0,2500,1,2,3,4,0,0
000001.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,PEAR,0,2500,1,2,3,4,0,0
000001.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,APPLE,1,5000,1,2,3,4,0,0
000001.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,BANANA,1,5000,1,2,3,4,0,0
000001.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,PEACH,0,2500,1,2,3,4,0,0
000001.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,PEAR,0,2500,1,2,3,4,0,0
000002.jpg,20000900400046,ONEVOTE VOTE FOR ONE,APPLE,1,5000,1,2,3,4,0,0
000002.jpg,20000900400046,ONEVOTE VOTE FOR ONE,BANANA,0,2500,1,2,3,4,0,0
000002.jpg,20000900400046,ONEVOTE VOTE FOR ONE,PEACH,0,2500,1,2,3,4,0,0
000002.jpg,20000900400046,ONEVOTE VOTE FOR ONE,PEAR,0,2500,1,2,3,4,0,0
000002.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,APPLE,1,5000,1,2,3,4,0,0
000002.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,BANANA,0,2500,1,2,3,4,0,0
000002.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,PEACH,0,2500,1,2,3,4,0,0
000002.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,PEAR,0,2500,1,2,3,4,0,0
000002.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,APPLE,1,5000,1,2,3,4,0,0
000002.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,BANANA,0,2500,1,2,3,4,0,0
000002.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,PEACH,0,2500,1,2,3,4,0,0
000002.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,PEAR,0,2500,1,2,3,4,0,0
000010.jpg,20000900400046,ONEVOTE VOTE FOR ONE,PEAR,0,2500,1,2,3,4,0,0
000010.jpg,20000900400046,ONEVOTE VOTE FOR ONE,APPLE,1,5000,1,2,3,4,0,0
000010.jpg,20000900400046,ONEVOTE VOTE FOR ONE,BANANA,1,5000,1,2,3,4,0,0
000010.jpg,20000900400046,ONEVOTE VOTE FOR ONE,PEACH,1,5000,1,2,3,4,0,0
000010.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,PEAR,0,2500,1,2,3,4,0,0
000010.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,APPLE,1,5000,1,2,3,4,0,0
000010.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,BANANA,1,5000,1,2,3,4,0,0
000010.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,PEACH,1,5000,1,2,3,4,0,0
000010.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,PEAR,0,2500,1,2,3,4,0,0
000010.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,APPLE,1,5000,1,2,3,4,0,0
000010.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,BANANA,1,5000,1,2,3,4,0,0
000010.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,PEACH,1,5000,1,2,3,4,0,0
000011.jpg,20000900400046,ONEVOTE VOTE FOR ONE,PEAR,0,2500,1,2,3,4,0,0
000011.jpg,20000900400046,ONEVOTE VOTE FOR ONE,APPLE,1,5000,1,2,3,4,0,0
000011.jpg,20000900400046,ONEVOTE VOTE FOR ONE,BANANA,1,5000,1,2,3,4,0,0
000011.jpg,20000900400046,ONEVOTE VOTE FOR ONE,PEACH,0,2500,1,2,3,4,0,0
000011.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,PEAR,0,2500,1,2,3,4,0,0
000011.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,APPLE,1,5000,1,2,3,4,0,0
000011.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,BANANA,1,5000,1,2,3,4,0,0
000011.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,PEACH,0,2500,1,2,3,4,0,0
000011.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,PEAR,0,2500,1,2,3,4,0,0
000011.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,APPLE,1,5000,1,2,3,4,0,0
000011.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,BANANA,1,5000,1,2,3,4,0,0
000011.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,PEACH,0,2500,1,2,3,4,0,0
000012.jpg,20000900400046,ONEVOTE VOTE FOR ONE,APPLE,1,5000,1,2,3,4,0,0
000012.jpg,20000900400046,ONEVOTE VOTE FOR ONE,BANANA,0,2500,1,2,3,4,0,0
000012.jpg,20000900400046,ONEVOTE VOTE FOR ONE,PEACH,0,2500,1,2,3,4,0,0
000012.jpg,20000900400046,ONEVOTE VOTE FOR ONE,PEAR,0,2500,1,2,3,4,0,0
000012.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,APPLE,1,5000,1,2,3,4,0,0
000012.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,BANANA,0,2500,1,2,3,4,0,0
000012.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,PEACH,0,2500,1,2,3,4,0,0
000012.jpg,20000900400046,TWOVOTES VOTE FOR NO MORE THAN TWO,PEAR,0,2500,1,2,3,4,0,0
000012.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,APPLE,1,5000,1,2,3,4,0,0
000012.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,BANANA,0,2500,1,2,3,4,0,0
000012.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,PEACH,0,2500,1,2,3,4,0,0
000012.jpg,20000900400046,THREEVOTES VOTE FOR NO MORE THAN THREE,PEAR,0,2500,1,2,3,4,0,0

TEST results:
mitch@mitch-HP-Compaq-6200-Pro-MT-PC:~/alt$ python overvote.py 
Command line args Namespace(allowed_votes=1, threshold=4000)
ONEVOTE VOTE FOR ONE,APPLE,6,2, over, 4
ONEVOTE VOTE FOR ONE,BANANA,6,0, over, 4
ONEVOTE VOTE FOR ONE,PEACH,6,0, over, 2
ONEVOTE VOTE FOR ONE,PEAR,6,0, over, 0
THREEVOTES VOTE FOR NO MORE THAN THREE,APPLE,6,6, over, 0
THREEVOTES VOTE FOR NO MORE THAN THREE,BANANA,6,4, over, 0
THREEVOTES VOTE FOR NO MORE THAN THREE,PEACH,6,2, over, 0
THREEVOTES VOTE FOR NO MORE THAN THREE,PEAR,6,0, over, 0
TWOVOTES VOTE FOR NO MORE THAN TWO,APPLE,6,4, over, 2
TWOVOTES VOTE FOR NO MORE THAN TWO,BANANA,6,2, over, 2
TWOVOTES VOTE FOR NO MORE THAN TWO,PEACH,6,0, over, 2
TWOVOTES VOTE FOR NO MORE THAN TWO,PEAR,6,0, over, 0

"""
