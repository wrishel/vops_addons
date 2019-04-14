"""Process the output from tevs_matcher creating vote counts by precinct."""

import os
import sys
stderr = sys.stderr
from DetailLine.DetailLine import *


# Containers for a Choice, Contest or Contestgroup.
#
# Contest Groups could be a precinct or the entire election.
#
class Choice(object):
    '''Summary of counts for a choice within a contest.'''

    def __init__(self, dl):
        self.name = dl.fuz_choice
        self.votes = 0
        self.undervotes = 0
        self.overvotes = 0

    def accumulate(self, dl):
        self.votes += int(dl.initial_voted)
        self.undervotes += int(dl.undervoted)
        self.overvotes += int(dl.initial_overvoted)


class Contest(object):
    '''The Choices for a contest.'''

    def __init__(self, dl):
        self.name = dl.fuz_contest
        self.choices = dict()

    def accumulate(self, dl):
        choice = self.choices.get(dl.fuz_choice, Choice(dl))
        choice.accumulate(dl)
        self.choices[dl.fuz_choice] = choice

class Precinct(object):
    def __init__(self, dl, name=None):
        '''Initialize with either or name.'''
        if name:
            self.name = name
        else:
            self.name = dl.pctid
        self.contests = dict()

    def accumulate(self, dl):
        contest = self.contests.get(dl.fuz_contest, Contest(dl))
        contest.accumulate(dl)
        self.contests[dl.fuz_contest] = contest

class PrecinctsGroup():
    '''A precinct or the entire election.'''

    def __init__(self):
        self.precincts = dict()

    def accumulate(self, dl):
        '''Accumulate in a precinct, creating it if necessary.'''

        pct = self.precincts.get(dl.pctid, Precinct(dl))
        pct.accumulate(dl)
        self.precincts[dl.pctid] = pct


# Support for setting up runtime parameters
#
class Params(object):   # https://stackoverflow.com/questions/1325673/how-to-add-property-to-a-class-dynamically/1333275
    pass

def insert_run_number(pth, base_file_name):
    # assert 'NN' in base_file_name
    return os.path.join(pth, base_file_name).replace('NN', params.FILE_NAME_SUFFIX)

params = Params()

# files
#
pth_current_run = os.getcwd() + '/'

# input from tevs_matcher
#
params.FILE_NAME_SUFFIX = '16'
pth_big_files = '/Users/Wes/NotForTheCloud/2018_Nov/in-process'
params.INF_DETAILS = insert_run_number(pth_big_files, 'details_fuzzy_overvNN.csv')
# params.INF_DETAILS = '/Users/Wes/NotForTheCloud/2018_Nov/in-process/testfuzovr3A--1MEAS_M.csv'
params.OUF_PCT_TOTALS = insert_run_number(pth_current_run, 'output/precinct_totalsNN.tsv')
params.OUF_CTY_TOTALS = insert_run_number(pth_current_run, 'output/county_totalsNN.tsv')
params.SHORT_RUN = None  # for debugging, read only this many input lines

# read the input and accumulate totals
#
lines_in = 0
precincts = PrecinctsGroup()
all_pcts = Precinct(None, '<Humb County>')

with open(params.INF_DETAILS, 'r') as details_in:
    for line in details_in:
        if line.strip() == '': continue
        try:
            dl = Detail_line(line)
            dl.undervoted               # test to see if got full line
        except Exception as e:
            stderr.write(str(lines_in) + ' ' + e.__repr__() + '\n')
            continue
        # print dl.pctid
        if dl.pctid == "None":
            dl.pctid = 'unknown'

        precincts.accumulate(dl)    # recursively accumulate
        all_pcts.accumulate(dl)     # county-side totals
        lines_in += 1
        if lines_in % 100000 == 0:
            print lines_in
        if params.SHORT_RUN and lines_in >= params.SHORT_RUN:
            break

    print lines_in

# output totals per contest in a precinct
#
with open(params.OUF_PCT_TOTALS, 'w') as ouf:
    fmt = '{}\t{}\t{}\t{}\t{}\t{}\n'
    ouf.write('Precinct\tContest\tChoice\tVotes\tOver Votes\tUnder Votes\n')
    for precinct in [precincts.precincts[pct_id] for pct_id in sorted(precincts.precincts.keys())]:
        for contest in [precinct.contests[x] for x in sorted(precinct.contests.keys())]:
            for choice in [contest.choices[x] for x in sorted(contest.choices.keys())]:
                ouf.write(fmt.format(precinct.name, contest.name, choice.name, \
                                     choice.votes, choice.overvotes, choice.undervotes))

# output totals per contest for the whole county
#
with open(params.OUF_CTY_TOTALS, 'w') as ouf:
    fmt = '{}\t{}\t{}\t{}\t{}\n'
    ouf.write('Contest\tChoice\tVotes\tOver Votes\tUnder Votes\n')
    for contest in [all_pcts.contests[x] for x in sorted(all_pcts.contests.keys())]:
        for choice in [contest.choices[x] for x in sorted(contest.choices.keys())]:
            ouf.write(fmt.format(contest.name, choice.name, \
                                 choice.votes, choice.overvotes, choice.undervotes))
