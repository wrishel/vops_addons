#!/usr/bin/env python2

"""
"""

import argparse
import csv
import errno
import os
import sys

class Vopitem(object):
    """_voted attribs are None or a vote count (potentially zero)"""

    def __init__(self, contest, choice, pct_id, barcode=None,
                 voph=None, voth=None, vopnt=None, votnt=None, vopot=None, votot=None):
        
        self.contest = contest
        self.choice = choice
        self.pct_id = pct_id
        self.voph = voph        # voteop HARTS
        self.voth = voth        # voted  HARTS
        self.vopnt = vopnt      # voteop new TEVS
        self.votnt = votnt      # voted  new TEVS
        self.vopot = vopot      # voteop old TEVS
        self.votot = votot      # voted  old TEVS
        # assert not barcode is None and  barcode.isdigits()
        self.barcode = barcode

    def __str__(self):
        s = '<Vopitem:'
        vs = ['{}: {}'.format(k, self.__dict__[k]) for k in sorted(self.__dict__.keys())]
        s += ', '.join(vs)
        return s + '>'

    def liststr(self):
        return  [self.contest, self.choice, self.pct_id, self.barcode,
                str(self.voph), str(self.voth), str(self.vopnt), str(self.votnt),
                str(self.vopot), str(self.votot)]


class Vops(dict):

    def __init__(self):
        super(Vops, Vops).__init__(self)

    def upd_rec_old_tevs (self, contest, choice, pct_id, barcode, voteops, votes):
        key = (contest, choice, pct_id)
        item = self.get(key, Vopitem(contest, choice, pct_id))
        item.vopot = add_to_none(item.vopot, voteops)
        item.votot = add_to_none(item.votot, votes)
        if barcode and barcode != '--na--':
            item.barcode = barcode
        self[key] = item

    def upd_rec_new_tevs (self, contest, choice, pct_id, barcode, voteops, votes):
        key = (contest, choice, pct_id)
        item = self.get(key, Vopitem(contest, choice, pct_id))
        item.vopnt = add_to_none(item.vopnt, voteops)
        item.votnt = add_to_none(item.votnt, votes)
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

    def upd_rec(self, contest, choice, voph, voth, votot, vopnt, votnt):
        key = (contest, choice)
        item = self.get(key, Vopitem(contest, choice, None))
        item.voph = add_to_none(item.voph, voph)
        item.voth = add_to_none(item.voth, voth)
        item.votot = add_to_none(item.votot, votot)
        item.vopnt = add_to_none(item.vopnt, vopnt)
        item.votnt = add_to_none(item.votnt, votnt)
        self[key] = item

    def iter_rec(self):
        for key in sorted(self.keys()):
            yield self[key]


def add_to_none(target, value):
    v1 = target if target else 0
    v2 = value  if value else 0
    return v1 + v2


def diff(x, y):
    if x is None:
        return y
    if y is None:
        return x
    return x - y


def get_clargs():
    argpars = argparse.ArgumentParser(description='Compare TEVS output to HARTS',
                                      prog=os.path.basename(__file__))
    argpars.add_argument('--progress', type=int, default=None,
                         help='report progress to stderr every N lines')
    argpars.add_argument('infile', nargs='?', type=argparse.FileType('r'),
        default = sys.stdin, help='HARTS consolidated counts')
    argpars.add_argument('--harts', type=argparse.FileType('r'),
        help='TEVS consolidated counts')
    argpars.add_argument('--oldtevs', type=argparse.FileType('r'),
        help='report with old tevs counts')
    argpars.add_argument('--rptdir', default='.',
        help='directory where report_pct.tsv and report_overall.tsv will be written, default "."')
    return argpars.parse_args()


# ---------------------------------------- MAIN ---------------------------------------- #

clargs = get_clargs()
stderr = sys.stderr

rptdir = clargs.rptdir

try:
    os.makedirs(rptdir)
except OSError as e:
    if not os.path.isdir(rptdir):
        raise

rptp = os.path.join(rptdir, 'report_both_pct.tsv')              # output
rpto = os.path.join(rptdir, 'report_both_overall.tsv')          # output
oldtevsf = clargs.oldtevs

lcnt = 0
vops = Vops()

if clargs.progress:
    stderr.write('PROCESSING TEVS NEW\n')

with clargs.infile as inf:
    for line in inf:
        lcnt += 1
        fields = line.split('\t')
        f = [x.strip() for x in fields]
        contest, choice, pct, barcode, voteops, votes = \
            f[0], f[1], f[2], f[3], int(f[4]), int(f[5])
        vops.upd_rec_new_tevs (contest, choice, pct, barcode, voteops, votes)

if clargs.progress:
    stderr.write('PROCESSING OLD TEVS\n')
with oldtevsf as newtf:
    for r in csv.DictReader(oldtevsf, dialect=csv.excel_tab):
        r['Choice'] = r['Choice'].upper()
        # r['Choice'] = r['Choice'].replace('"', '')
        if r['Contest'] + r['Choice'] + r['Precinct'] == '':
            continue
        contest, choice, pct, barcode, votes = \
            r['Contest'], r['Choice'], r['Precinct'][3:], r['template'], int(r['TEVS Count'])
        vops.upd_rec_old_tevs (contest, choice, pct, barcode, None, votes)



if clargs.progress:
    stderr.write('PROCESSING HARTS\n')

with clargs.harts as inf:
    for line in inf:
        lcnt += 1
        # line = line.replace('"', '')
        line = line.replace('Write-In', 'WRITE-IN')
        fields = line.split('\t')
        f = [x.strip() for x in fields]
        contest, choice, pct, voteops, votes = f[1], f[2], f[0], int(f[3]), int(f[4])
        vops.upd_rec_harts(contest, choice, pct, voteops, votes)


# emit comparison by precinct
#
with open(rptp, 'w') as ouf:
    headitems = ['contest', 'choice', 'precinct', 'barcode', 'HARTS Vote Ops', 'New TEVS Vote Ops',
                 'HARTS Votes', 'New TEVS Votes', 'Old TEVS Votes', 'Vote Ops HARTS v New TEVS',
                 'Votes HARTS v New TEVS', 'Votes HARTS v Old TEVS', 'Votes New TEVS v Old TEVS']
    headline = '\t'.join(headitems) + '\n'
    ouf.write(headline)
    for v in vops.iter_rec():
        outv = [v.contest, v.choice, v.pct_id, v.barcode, v.voph, v.vopnt,
                v.voth, v.votnt, v.votot,
                diff(v.voph, v.vopnt), diff(v.voth, v.votnt),
                diff(v.voth, v.votot), diff(v.votnt, v.votot)]
        outv = [str(x) for x in outv]
        outv[2] = '~  ' + outv[2]     # keep Excel from turning pct_id into a floating point number
        ouf.write('\t'.join(outv) + '\n')

# compute totals for entire election
#
vopstots = Vopstots()
for v in vops.iter_rec():
    vopstots.upd_rec(v.contest, v.choice, v.voph, v.voth, v.votot, v.vopnt, v.votnt)

# compute margins & tack onto vopitems in vopstots
#
contests = set((v.contest for v in vopstots.iter_rec()))
margins = dict()                    # margin for a contest across all precincts
for contest in contests:
    choices = [v for v in vopstots.iter_rec() if v.contest == contest]
    choices = sorted(choices, key=lambda v: v.voth, reverse=True)
    margins[contest] = choices[0].voth - choices[1].voth




# emit county-wide totals
#

with open(rpto, 'w') as ouf:
    headitems = ['contest', 'choice', 'HARTS Vote Ops', 'New TEVS Vote Ops', 'HARTS Votes', \
                'New TEVS Votes', 'Old TEVS Votes', 'Vote Ops HARTS v New TEVS',
                 'Votes HARTS v New TEVS', 'Votes HARTS v Old TEVS', 'Votes New TEVS v Old TEVS',
                 '% of Margin']
    headline = '\t'.join(headitems) + '\n'
    ouf.write(headline)
    for v in vopstots.iter_rec():
        vop_hart_v_newtevs = diff(v.voph, v.vopnt)
        vot_hart_v_newtevs = diff(v.voth, v.votnt)
        vot_hart_v_oldtevs = diff(v.voth, v.votot)
        vot_newtevs_v_oldtevs = diff(v.votnt, v.votot)
        percent_margin = float(vot_hart_v_newtevs) / margins[v.contest]

        outv = [v.contest, v.choice, v.voph, v.vopnt, v.voth, v.votnt, v.votot,
                vop_hart_v_newtevs, vot_hart_v_newtevs, vot_hart_v_oldtevs,
                vot_newtevs_v_oldtevs, percent_margin
               ]
        outv = [str(x) for x in outv]
        ouf.write('\t'.join(outv) + '\n')
