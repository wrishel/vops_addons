"""Use ModelElection to fuzzy-match the output from voteops details with an election.

Written and copyright by Wes Rishel, wrishel (funny circle with a 'a' in it) gmail

This program runs after Vops, aka the new version of the Trachtenberg Election Voting System.

Its main input is a details.csv file created by Vops.

"""
import csv
import datetime
import os
import re
import sys
import time

from ModelElection.ModelElection import *
from DetailLine.DetailLine import *

'''

    parameters set at top of main:
        # imagesp
        max_image_number
        detailsp  params.INF_DETAILS
        params.OUT_UNMATCHED_PCTIDS
        params.OUF_TOTALS  # output for comparison by precinct group
        details_outp
        official_datap
        hardmatches
    
    objects
        detail_line_ext 
        file_names
        unmatched_contests detail.line object key is detail_line.choice
        unmatched_choices (name, contest, barcode, filename, details line number)
        unmatched_precinct_IDs (details line)
        details_out_lines

    initialize
        file_names from imagesp
        create details_output file 
        create unmatched_contests
        create unmatched_choices
        create unmatched_precinct_IDs
        create details_includes set
        hm = hardmatches
        
    
    workflow
        print report header
        
        for each row in details.csv
            progress report
            if image number > max_image_number
                # accumulate image numbers skipped
                continue
            create out_line object with input line details
            if output_line.file name in details_includes
            delete file name from all file names (may already be deleted)
            lookup precinct id by barcode
            if precinct_id not found
                add item to unmatched_precinct_IDs
            add precinct_id to out_line
            add fuzzy contest to utline
            if fuzzy contest is none
                add item to unmatched_contests
                add item to unmatched_choices
            else
                add fuzzy choice to out_line
                if fuzzy choice is none
                    add item to unmatched_choices
                            
        header for unmatched precinct ids
        print unmatched_precinct_ids
                    
        header for unmatched_contests
        print unmatched_contests
                    
        header for unmatched_choices
        print unmatched_choices
'''

# INITIALIZATION

details_includes = set()
for x in [      # '010097.jpg'
    ]:
        details_includes.add(x)


class Rprint(object):
    '''Used to tee output to terminal and the fuzzy report.'''

    def __init__(self, outfname):
        self.outf = open(outfname, 'w')

    def write(self, *args):
        '''send to stdout and the report'''

        s = ' '.join((str(x) for x in args))
        self.outf.write(s + '\n')
        print s


def pct(count, base):
    """Return a percentage of the two, which may be integers."""

    if base == 0:
        return 0.0
    return 100 * float(count) / base

def pcts(count, base):
    return '{:.3f}%'.format(pct(count, base))

class Counter(dict):
    def __init__(self):
        super(Counter, Counter)

    def add(self, item):
        self[item] = self.get(item, 0) + 1

    def sort_by_prevalence(self):
        l = [(self[x], x) for x in self]
        sl = sorted(l, reverse=True)
        return sl


class Accum(object):
    def __init__(self):
        self.d = {}

    def add(self, item, value):
        lset, lcnt = self.d.get(item, (set(), 0))
        lset.add(value)
        lcnt += 1
        self.d[item] = (lset, lcnt)

    def __str__(self):
        s = ''
        for k in sorted(self.d):
            s += '{}  {}\n'.format(k, self.d[k][1])
            for v in self.d[k][0]:
                s += '            {}\n'.format(v)
        return s

class AccumWithLine(Accum):
    '''Accumulate lines with unmatched items by item'''

    def add(self, item, line):
        lcnt, lines = self.d.get(item, (0, []))
        lines.append(line)
        lcnt += 1
        self.d[item] = (lcnt, lines)

    def __iter__(self):
        '''return the key, the count, and the detail lines sorted by order of keys'''

        for k in sorted(self.d.keys()):
            yield (k, self.d[k][0], self.d[k][1])


class Accumwcnt(object):
    """Accum with count. For each master value list and count the associate values"""

    def __init__(self):
        self.d = {}

    def add(self, item, assocvalue):
        itemcntr = self.d.get(item, Counter())
        itemcntr.add(assocvalue)
        self.d[item] = itemcntr

    def __str__(self):
        items = ['{}: {}'.format(str(k), str(self.d[k])) for k in sorted(self.d.keys())]

        s = '<Accumwcnt: '
        s += '; '.join(items)
        s += '>'
        return s

    def fancy_out(self, elimspace=False):
        """Return a string of lines indented with the associated values sorted by prevalence"""

        s = ''
        for k in sorted(self.d.keys()):
            s += '\n    ' + str(k) + '\n'
            cntr = self.d[k]
            matches = []
            for matched_item in cntr.sort_by_prevalence():
                oline = '        {} ({})'.format(matched_item[1], matched_item[0])
                compval = k
                if elimspace:
                    compval = compval.replace(' ','')

                if matched_item[1] == compval:
                    oline += ' (*)'

                matches.append(oline)
            s += '\n'.join(matches) + '\n'
        return s


class Tevs_options(object):
    '''This class is just a way to centralize as many hacks as possible.'''

    def __init__(self, incsv, includes=None):
        """incsv is an iterable of comma separated lines;
        includes is a list of file namess to accept. If None, all are accepted."""

        self.incsv = incsv
        self.linecnt = -1
        self.include_files = includes

    def __iter__(self):
        """Return a Detail_line object."""
        with open(self.incsv) as data:
            for ll in data.readlines():

                # do this as early as possible to speed up test runs
                #
                if self.include_files and ll[:10] not in self.include_files:
                    continue
                ll = whole_input_line_hacker.hack(ll)
                retval = Detail_line(ll)
                self.linecnt += 1

                # various hacks on contest name
                #
                # contest = retval.contest
                # contest = contest.replace('"', '')
                # contest = re.sub(r' *VOTE FOR (ONE|TWO|THREE|FOUR|FIVE)',    # increase fuzzy discrimination
                #             '', contest)

                # retval.contest = contest
                # mo = re.match(r'PROPOSITION (?P<digits>\d{3,})', contest)
                # if mo:
                #     retval.contest = 'PPROPOSITION ' + mo.group('digits')[1:]
                #     sys.stderr.write('{}: attempting to fix proposition {}\n'\
                #                      .format(self.linecnt, ll))

                yield retval

    # def reassemble(self, contest, choice):
    #     """Assemble the parameters plus the original tuple"""
    #
    #     return ','.join(self.current + [str(contest), str(choice)])

    def fixfilename(self, s):
        return s.lower()

class hacker(object):
    def __init__(self, list):
        self.list = list

    def hack(self, value):
        v = value
        for pattern, replacement in self.list:
            value = re.sub(pattern, replacement, value)
        # if v != value:
        #     print 'hack in', v.strip()
        #     print 'hackout', value
        return value

# ---------------------------------------- MAIN ---------------------------------------- #

whole_input_line_hacker = hacker([
    (r'PROPOSITION 114', 'PROPOSITION 14'),
    (r'"', ''),
    (r' *VOTE FOR (ONE|TWO|THREE|FOUR|FIVE)', ''), # increase fuzzy discrimination
])

input_contest_hacker = hacker([

])


start= time.time()

# These items could be created by commandline parsing, but not now
max_image_number = '299999'

# general paramaters
#
class Params(object):   # https://stackoverflow.com/questions/1325673/how-to-add-property-to-a-class-dynamically/1333275
    pass

params = Params()
params.INCLUDES =   None #  ['005412.jpg']   # for debugging
params.PROG_REPORT = 100000
params.SHORT_RUN = 10000
if params.SHORT_RUN:
    params.PROG_REPORT = int(params.SHORT_RUN/10)


# files
#
pth_current_run = os.getcwd() + '/'

# input from vops
#
params.INF_DETAILS = pth_current_run + 'vops/' + 'details181202.csv'

# input files from Elections Department
#
pth_elections_static = pth_current_run + 'static_2018_nov/'
params.INF_HARTS_PRECINCTS = pth_elections_static + 'precincts_massaged.txt' #'precincts.tsv'
# params.INF_HARTS_TOTS = pth_elections_static + 'from_elections/General_blank_report.txt.csv'
params.INF_HARD_MATCHES = pth_elections_static + 'hard_matches.tsv'
params.INF_ELECTION_MODEL = pth_elections_static + 'ElectionModel.txt'   #tsv, no headers

# output files
#
output_dir = pth_current_run + 'output/'
params.OUT_REPORT = output_dir + 'fuzzy_report.txt'
params.OUT_UNMATCHED_PCTIDS = output_dir + 'unmatchedpctids.tsv'
params.OUT_DETAILS = output_dir + 'details_fuzzy.csv'

rprint = Rprint(params.OUT_REPORT).write
rprint('START TIME: ' + str(datetime.datetime.now()))
rprint('DETAILS INPUT FILE' + params.INF_DETAILS)

ee = Election('2018 November')
ee.load(open(params.INF_ELECTION_MODEL, 'r'))

with open(params.INF_HARD_MATCHES) as hardm:
    hm = hardmatches(hardm)

precinctids = dict()
with open(params.INF_HARTS_PRECINCTS) as precidf:
    rd = csv.reader(precidf, delimiter="\t", quotechar='"')
    for row in rd:
        precinctids[row[0]] = row[1]

tot_records = 0
bad_choice_tot = 0
bad_contests = 0
barcode_no_pctid = Accum()
barcode_no_match = Accum()
# cont_accum = Accumwcnt()
choice_accum = Accumwcnt()
unmatched_contests = AccumWithLine()
unmatched_choices = AccumWithLine()

# get entries from details.csv
#

inp_opt = Tevs_options(params.INF_DETAILS, params.INCLUDES)
rprint('\nLOADING ITEMS FROM DETAILS.CSV ' + params.INF_DETAILS)
det_fuzz = open(params.OUT_DETAILS, 'w')
lcnt = 0

# main processing loop
#
for dl in inp_opt:
    dl.file = inp_opt.fixfilename(dl.file)
    if len(details_includes) and dl.file not in details_includes:
        continue
    if lcnt % params.PROG_REPORT == 0:
        rprint('lines: ', lcnt, 'time: ', time.time() - start, dl.file)
    if params.SHORT_RUN and lcnt > params.SHORT_RUN:
        break

    lcnt += 1

    precinct_id = precinctids.get(dl.barcode[1:8], None)
    dl.pctid = precinct_id

    if precinct_id == None:
        barcode_no_pctid.add(dl.barcode, file)

    thiscont = ee.fuzmatch(dl.contest)
    if thiscont is None:

        # attempt cheat-match of contest by identifying choice
        #
        cheatname = ee.fuzmatch_all_choices(dl.choice)
        if cheatname:
            thiscont = ee.fuzmatch(cheatname.contest)

        if thiscont is None:
            bad_contests += 1
            unmatched_contests.add(dl.contest, dl)
            continue        # give up on this detail line


    dl.fuz_contest = thiscont.name
    # cont_accum.add(thiscont.name, dl.contest)

    thischoice = thiscont.fuzmatch(dl.choice)
    if thischoice:
        name = thischoice.name          # all matched up

    else:
        hmc_name = hm.match(dl.choice)
        if hmc_name:
            name = hmc_name
            rprint('hard match:', dl.choice, '>', hmc_name)

        else:

            # attempt: find a contest name that actually matches the choice
            #
            cheatname = ee.fuzmatch_all_choices(dl.choice)
            if cheatname:
                thiscont = ee.fuzmatch(cheatname.contest)
                if  thiscont == None:
                    bad_choice_tot += 1
                    unmatched_choices.add(dl.choice + ' in ' + dl.contest, dl)
                    det_fuzz.write(dl.output())
                    continue

                else:
                    # replace the fake contest with a real one
                    #
                    thiscont = ee.fuzmatch(thiscont.name)
                    thischoice = thiscont.fuzmatch(cheatname.name)
                    name = thischoice.name

    dl.fuz_choice = name
    choice_accum.add(name, dl.choice)
    tot_records += 1

rprint('fuzzy match failures from details.csv contests: {}, choices: {}'.format(pcts(bad_contests, tot_records), pcts(bad_choice_tot,  tot_records)))
rprint('Input lines from details: {}; lines fully processed from details: {} '\
        .format(inp_opt.linecnt, tot_records))

db_not_details = 0
details_not_db = 0
in_both_sources = 0
diff_vote_counts = 0
files_not_in_details = Accum()

rprint('\nBARCODES UNMATCHED WITH ' + params.INF_HARTS_PRECINCTS)
keys = barcode_no_pctid.d.keys()
if len(keys) == 0:
    rprint('--none--')
print barcode_no_pctid.d
for k in sorted(keys):
    rprint('{:9} {}'.format(barcode_no_pctid.d[k], k))

rprint('\nunmatched contest = {}; unmatched choices ={}'
       .format(bad_contests, bad_choice_tot))

rprint('\nUNMATCHED CONTESTS IN DETAILS.CSV')
unm = []
for x in unmatched_contests:
    unm.append((x[0], x[1], x[2]))   # contest name, count of entries, all detail lines

if len(unm) == 0:
    rprint('--none--')
else:
    for x in unm:
        rprint('   {:28} {:4d} {:6.2f}%'
               .format(x[0], x[1], 100.0 * x[1] / tot_records))
        # for item in x[2]:
        #     rprint(item)

rprint('\nUNMATCHED CHOICES IN DETAILS.CSV')
unm = list((x) for x in unmatched_choices)
if len(unm) == 0:
    rprint('--none--')
else:
    for x in unm:
        rprint('   {:28} {:4d} {:6.2f}%'\
               .format(x[0], x[1], 100.0 * x[1] / tot_records))
        # for item in x[2]:
        #     rprint(item)
