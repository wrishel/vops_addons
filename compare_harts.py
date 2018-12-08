#!/usr/bin/env python2

"""
"""

import argparse
import errno
import os
import sys

class Vopitem(object):
    """_voted attribs are None or a vote count (potentially zero)"""

    def __init__(self, contest, choice, pct_id, barcode=None,
                 voph=None, voth=None, vopt=None, vott=None):
        self.contest = contest
        self.choice = choice
        self.pct_id = pct_id
        self.voph = voph        # voteop HARTS
        self.voth = voth        # voted HARTS
        self.vopt = vopt        # voteop TEVS
        self.vott = vott        # voted TEVS
        self.barcode = barcode

    def __str__(self):
        s = '<Vopitem:'
        vs = ['{}: {}'.format(k, self.__dict__[k]) for k in sorted(self.__dict__.keys())]
        s += ', '.join(vs)
        return s + '>'

    def liststr(self):
        return  [self.contest, self.choice, self.pct_id, self.barcode,
                str(self.voph), str(self.voth), str(self.vopt), str(self.vott)]


class Vops(dict):

    def __init__(self):
        super(Vops, Vops).__init__(self)

    def upd_rec_tevs(self, contest, choice, pct_id, barcode, voteops, votes):
        key = (contest, choice, pct_id)
        item = self.get(key, Vopitem(contest, choice, pct_id))
        item.vopt = add_to_none(item.vopt, voteops)
        item.vott = add_to_none(item.vott, votes)
        item.barcode = barcode
        self[key] = item

    def upd_rec_harts(self, contest, choice, pct_id, voteops, votes):
        key = (contest, choice, pct_id)
        item = self.get(key, Vopitem(*key))
        item.voph = add_to_none(item.voph, voteops)
        item.voth = add_to_none(item.voth, votes)
        self[key] = item

    def iter_rec(self):
        for key in sorted(self.keys()):
            yield self[key]


class Vopstots(dict):
    """Totals across precincts."""

    def __init__(self):
        super(Vopstots, Vopstots).__init__(self)

    def upd_rec(self, contest, choice, voph, voth, vopt, vott):
        key = (contest, choice)
        item = self.get(key, Vopitem(contest, choice, None))
        item.voph = add_to_none(item.voph, voph)
        item.voth = add_to_none(item.voth, voth)
        item.vopt = add_to_none(item.vopt, vopt)
        item.vott = add_to_none(item.vott, vott)
        self[key] = item

    def iter_rec(self):
        for key in sorted(self.keys()):
            yield self[key]


def add_to_none(target, value):
    v1 = target if target else 0
    v2 = value  if value else 0
    return v1 + v2


def absdiff(x, y):
    if x is None:
        return y
    if y is None:
        return x
    return abs(x - y)


def get_clargs():
    argpars = argparse.ArgumentParser(description='Compare TEVS output to HARTS',
                                      prog=os.path.basename(__file__))
    argpars.add_argument('--progress', type=int, default=None,
                         help='report progress to stderr every N lines')
    argpars.add_argument('infile', nargs='?', type=argparse.FileType('r'),
        default = sys.stdin, help='HARTS consolidated counts')
    argpars.add_argument('--harts', type=argparse.FileType('r'),
        help='TEVS consolidated counts')
    argpars.add_argument('--rptdir', default='.',
        help='directory where report_pct.tsv and report_overall.tsv will be written, default "."')
    return argpars.parse_args()


# ---------------------------------------- MAIN ---------------------------------------- #

clargs = get_clargs()
# SHORT_RUN = clargs.short
stderr = sys.stderr

rptdir = clargs.rptdir

try:
    os.makedirs(rptdir)
except OSError as e:
    if not os.path.isdir(rptdir):
        raise

rptp = os.path.join(rptdir, 'report_pct.tsv')
rpto = os.path.join(rptdir, 'report_overall.tsv')

lcnt = 0
vops = Vops()

if clargs.progress:
    stderr.write('PROCESSING TEVS\n')

with clargs.infile as inf:
    for line in inf:
        lcnt += 1
        fields = line.split('\t')
        f = [x.strip() for x in fields]
        contest, choice, pct, barcode, voteops, votes = \
            f[0], f[1], f[2], f[3], int(f[4]), int(f[5])
        vops.upd_rec_tevs(contest, choice, pct, barcode, voteops, votes)

if clargs.progress:
    stderr.write('PROCESSING HARTS\n')

with clargs.harts as inf:
    for line in inf:
        lcnt += 1
        line = line.replace('"', '')
        line = line.replace('Write-In', 'WRITE-IN')
        fields = line.split('\t')
        f = [x.strip() for x in fields]
        contest, choice, pct, voteops, votes = f[1], f[2], f[0], int(f[3]), int(f[4])
        vops.upd_rec_harts(contest, choice, pct, voteops, votes)

vopstots = Vopstots()

# generate comparison by district
#
with open(rptp, 'w') as ouf:
    headitems = ['contest', 'choice', 'precinct', 'barcode', 'HARTS Vote Ops', 'HARTS Votes', \
                'TEVS Vote Ops', 'TEVS Votes', 'Diff Vote Ops', "Diff Votes"]
    headline = '\t'.join(headitems) + '\n'
    ouf.write(headline)
    for v in vops.iter_rec():
        vopstots.upd_rec(v.contest, v.choice, v.voph, v.voth, v.vopt, v.vott)
        outv = v.liststr() + [absdiff(v.vopt, v.voph), absdiff(v.vott, v.voth)]
        outv = [str(x) for x in outv]
        outv[2] = '~  ' + outv[2]     # keep Excel from turning pct_id into a floating point number
        ouf.write('\t'.join(outv) + '\n')


# generate margins
#
margins = dict()
for k in vopstots.keys():
    item = vopstots[k]
    votecounts = margins.get(item.contest, [])
    votecounts.append(item.voth)
    margins[item.contest] = votecounts

for k in margins.keys():
    votecounts = sorted(margins[k])
    assert len(margins) > 1
    margins[k] = votecounts[-1] - votecounts[-2]


# generate county-wide totals
#
with open(rpto, 'w') as ouf:
    headitems = ['contest', 'choice', 'HARTS Vote Ops', 'HARTS Votes', \
                'TEVS Vote Ops', 'TEVS Votes', 'Diff Vote Ops', "Diff Votes", "Margin", "Diff / Margin"]
    headline = '\t'.join(headitems) + '\n'
    ouf.write(headline)
    for v in vopstots.iter_rec():
        votediff = absdiff(v.vott, v.voth)
        diffmarg = float(votediff) / margins[v.contest]
        outv = [v.contest, v.choice, v.voph, v.voth, v.vopt, v.vott,
                votediff, absdiff(v.vott, v.voth), margins[v.contest], diffmarg]
        outv = [str(x) for x in outv]
        ouf.write('\t'.join(outv) + '\n')
