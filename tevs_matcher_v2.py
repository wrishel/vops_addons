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

                # Eliminate input about ballot images no in the test set.
                # Do this as early as possible to speed up test runs
                #
                if self.include_files and ll[:10] not in self.include_files:
                    continue
                ll = whole_input_line_hacker.hack(ll)
                retval = Detail_line(ll)
                retval.contest = input_contest_hacker.hack(retval.contest)
                barcode_hacker(retval, barcode_hacklist)
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

class hacker(object):           # TODO: report which items were used.
    '''List of ['S or R, old-value, new-value]

       S means use string substitution. R means use regex.'''

    def __init__(self, list):
        self.list = list

    def hack(self, value):
        v = value
        for type, pattern, replacement in self.list:
            if type.upper() == 'R':
                value = re.sub(pattern, replacement, value)
            elif type.upper() == 'S':
                value = value.replace(pattern, replacement)
            else:
                raise ValueError('"{}" is not a valid replacement type'.format(type))

        return value

def barcode_hacker(dl, hacklist):
    for bc_hack in hacklist:
        if dl.barcode == bc_hack[0]:
            dl.corrected_barcode = bc_hack[1]
            break

    if dl.corrected_barcode is None:
        dl.corrected_barcode = dl.barcode

# hacks to fix specific input problems

whole_input_line_hacker = hacker([
    ('S', "\xe2\x80\x98", ''),                       # eliminate single quotes passed by vops
])

barcode_hacklist = [
    ("09637383686383", '20000820300065'),  # bar-code correction
    ("20001087677706", '20001050300063'),  # bar-code correction
]

input_contest_hacker = hacker([
    ('S', 'LOLETA UNION SCHOOL DISTRICT GOVERNING BOARD MEMBER 4YR VOTE',
          'LOLETA UNION SCHOOL DISTRICT GOVERNING BOARD MEMBER 4YR VOTE FOR NO MORE THAN THREE'),
    ('S', 'BEING INVESTIGATED OR PROSECUTED FOR CRIMINAL ACTIVITY',
            'MEASURE K HUMBOLDT COUNTY IMMIGRATION SANCTUARY ORDINANCE MEASURE'),
    ('S', 'RICHMAN BE ELECTED TO THE OFFICE FOR TERM PROVIDED BY LAW',
            'COURT OF APPEAL-ASSOCIATE JUSTICE-DISTRICT 1 DIVISION 2 JAMES A. RICHMAN'),
    ('S', 'RICHMAN BE ELECTED TO THE OFFICE FOR T TERM PROVIDED BY LAW',
            'COURT OF APPEAL-ASSOCIATE JUSTICE-DISTRICT 1 DIVISION 2 JAMES A. RICHMAN'),
    ('S', 'MARGULIES BE ELECTED TO THE OFFICE F THE TERM PROVIDED BY',
            'COURT OF APPEAL-ASSOCIATE JUSTICE-DISTRICT 1 DIVISION 1 SANDRA MARGULIES'),
    ('S', 'ER EE 6 ELIMINATES CERTAIN ROAD REPAIR AND TRANSPORTATION',
            'MEASURE K HUMBOLDT COUNTY IMMIGRATION SANCTUARY ORDINANCE MEASURE'),
    ('S', 'INCREASE IN TAX RATE BE AQOPTED',
            'MEASURE O HUMBOLDT COUNTY PUBLIC SAFETY/ESSENTIAL SERVICES RENEWAL'),
    ('S', 'QELRENLORAUNY TUADO AIL OUICT COOTIILIC GENERAL SERVICES S',
            'MEASURE O HUMBOLDT COUNTY PUBLIC SAFETY/ESSENTIAL SERVICES RENEWAL'),
    ('S', 'GQCLENHUORALILY UAE AI UUTET COOTTILILE GENERAL SERVICES SHA',
            'MEASURE O HUMBOLDT COUNTY PUBLIC SAFETY/ESSENTIAL SERVICES RENEWAL'),
    ('S', 'QELENLORAUNLG TODDO ALU OUI COOTIIC GENERAL SERVICES SHALL',
            'MEASURE O HUMBOLDT COUNTY PUBLIC SAFETY/ESSENTIAL SERVICES RENEWAL'),
    ('S', 'ANNUALLY UNTIL ENDED BY VOTERS WITH NN NY ANNUAL AUDITSCITIZEN OVERSIGHT',
     'MEASURE O HUMBOLDT COUNTY PUBLIC SAFETY/ESSENTIAL SERVICES RENEWAL'),
    ('S', 'NEE NAP EA ENELENEA TOU EEN','CITY OF EUREKA MAYOR'),
])

class Params(object):   # https://stackoverflow.com/questions/1325673/how-to-add-property-to-a-class-dynamically/1333275
    pass

def unique_output_name(base_name, outputdir):
    of = os.path.join(outputdir, base_name)
    while os.path.isfile(of):
        file = os.path.basename(of)
        fname = file[:-4]
        fnum = int(fname[-2:])
        if fnum > 99:
            of = 'fuzzy_report00.txt'
            return of
        else:
            fnum = fnum + 1
            of = pth_small_outputs + 'fuzzy_report' + '{:02d}'.format(int(fnum)) + '.txt'

    return of

# ---------------------------------------- MAIN ---------------------------------------- #

start= time.time()
params = Params()   # in the future some of these man be command line parameters

# paths to major file groups
#
pth_current_run = os.getcwd() + '/'
pth_big_files = '/Users/Wes/NotForTheCloud/2018_Nov/in-process'
pth_elections_static = pth_current_run + 'data/static_2018_nov/'
pth_small_outputs = pth_current_run + 'output/'

# general paramaters
#
params.INCLUDES = [] #'024681.jpg']    # for debugging
params.PROG_REPORT = 100000
params.SHORT_RUN = None                     # for debugging
if params.SHORT_RUN:
    params.PROG_REPORT = int(params.SHORT_RUN/10)


#   input from vops
#
params.INF_DETAILS = os.path.join(pth_big_files, 'details190106.csv')
                                  # 'testdetails.csv')

#   input files from that describe the election
#
params.INF_HARTS_PRECINCTS = pth_elections_static + 'precincts_massaged.txt' #'precincts.tsv'
params.INF_HARD_MATCHES = pth_elections_static + 'hard_matches.tsv'
params.INF_ELECTION_MODEL = pth_elections_static + 'ElectionModel.txt'   #tsv, no headers

#       certain outputs get a unique file name for each run (at least while debugging)
#


of = unique_output_name('fuzzy_report14.txt', pth_big_files)

output_vnum = of[-6:-4]     # uhique suffix for output files for this run

params.OUT_REPORT = of
params.OUT_UNMATCHED_PCTIDS = os.path.join(pth_small_outputs, 'unmatchedpctids' + output_vnum + '.tsv')
params.OUT_DETAILS = os.path.join(pth_big_files, 'details_fuzzy' + output_vnum + '.csv')

outdtf = open(params.OUT_DETAILS, 'w')
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

    precinct_id = precinctids.get(dl.corrected_barcode[1:8], None)
    dl.pctid = precinct_id

    if precinct_id == None:
        barcode_no_pctid.add(dl.corrected_barcode, file)
    # print dl.contest
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
    outdtf.write(dl.output())
    choice_accum.add(name, dl.choice)
    tot_records += 1

# report outputs
#
rprint('fuzzy match failures from details.csv contests: {}, choices: {}'.format(pcts(bad_contests, tot_records), pcts(bad_choice_tot,  tot_records)))
rprint('Input lines from details: {}; lines fully processed from details: {} '\
        .format(inp_opt.linecnt, tot_records))  # TODO: totals off by one
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
        if tot_records:
            rprint('   {:28} {:4d} {:6.2f}%'
                   .format(x[0], x[1], 100.0 * x[1] / tot_records))
            for dl in x[2][:5]:
                rprint(dl.file)
        else:
            rprint('   {:28} {:4d}'
                   .format(x[0], x[1]))
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

rprint('\nCONFIGURED HARD SUBSTITUTIONS FOR ANYWHERE IN LINE:')
for x in whole_input_line_hacker.list:
    rprint('\t{} --> {}'.format(x[1], x[2]))

rprint('\nCONFIGURED HARD SUBSTITUTIONS FOR CONTEST:')
for x in input_contest_hacker.list:
    rprint('\t{} --> {}'.format(x[1], x[2]))

rprint('\nCONFIGURED HARD SUBSTITUTIONS FOR BARCODE:')
for x in barcode_hacklist:
    rprint('\t{} --> {}'.format(x[0], x[1]))

