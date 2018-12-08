#!/usr/bin/env python2

"""
"""

import argparse
import os
import sys

from ModelElection.ModelElection import *

class Consolidater(dict):
    def __init__(self):
        super(Consolidater, Consolidater)

    def upd_rec(self, contest, choice, barcode, voteops, votes):
        key = (contest, choice, barcode)
        item = self.get(key, [0, 0])
        item[0] += voteops
        item[1] += votes
        self[key] = item

    def get_rec(self, contest, choice, barcode):
        return self[(contest, choice, barcode)]

    def iter_rec(self):
        for key in sorted(self.keys()):
            yield list(key) + self[key]

def barc_subset(barcode):
    """Extract the portion of the barcode that identifies a precinct."""
    return barcode[1:8]

def get_clargs():
    argpars = argparse.ArgumentParser(description='Convert TEVS to consolidated vote counts',
                                      prog=os.path.basename(__file__))

    argpars.add_argument('--pct', type=argparse.FileType('r'),
                         help='barcode to pct_id conversion file')

    argpars.add_argument('--short', type=int, default=None,
                         help='number of items in short run (for debugging)')

    argpars.add_argument('--progress', type=int, default=None,
                         help='report progress to stderr every N lines')

    argpars.add_argument('infile', nargs='?', type=argparse.FileType('r'),
        default = sys.stdin, help='input from vops run, default stdin')

    argpars.add_argument('outfile', nargs='?', type=argparse.FileType('w'),
        default = sys.stdout, help='output file, default stdout')

    return argpars.parse_args()


# ---------------------------------------- MAIN ---------------------------------------- #

clargs = get_clargs()
SHORT_RUN = clargs.short

lcnt = 0

consoldt = Consolidater()

bc_to_pct = dict()
if clargs.pct:
    with clargs.pct as pctf:
        for line in pctf.readlines():
            pct_id, barc = (x.strip() for x in line.split('\t'))
            bc_to_pct[barc] = pct_id

with clargs.infile as inf:
    for line in inf:
        lcnt += 1
        if SHORT_RUN and lcnt > SHORT_RUN:
            break
        if clargs.progress and lcnt % clargs.progress == 0:
            sys.stderr.write('{} lines; {} outputs\n'.format(lcnt, len(consoldt)))
        fields = line.split('\t')
        f = [x.strip() for x in fields]
        contest, choice, barcode, voteops, votes = f[-2], f[-1], f[1], 1, int(f[4])
        consoldt.upd_rec(contest, choice, barcode, voteops, votes)


for contest, choice, barcode, voteops, votes in consoldt.iter_rec():
    precinct = bc_to_pct.get(barc_subset(barcode), barc_subset(barcode))
    x = '\t'.join((contest, choice, precinct, barcode, str(voteops), str(votes)))
    clargs.outfile.write(x + '\n')

with sys.stderr as reportf:
    reportf.write('Lines read: ' + str(lcnt) + '\n')
    reportf.write('Lines out: ' + str(len(consoldt)) + '\n')
