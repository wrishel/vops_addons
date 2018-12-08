"""Process the output from tevs_matcher creating vote counts by precinct."""

import os
import sys
stderr = sys.stderr
from DetailLine.DetailLine import *

class PrecContChoicTotvotes(dict):
    def add(self, precinct, contest, choice, votes):
        key = (precinct, contest, choice)
        this = self.get(key, 0)
        this += int(votes)
        self[key] = this

class ContChoicTotvotes(dict):
    def add(self, contest, choice, votes):
        key = (contest, choice)
        this = self.get(key, 0)
        this += int(votes)
        self[key] = this

class Params(object):   # https://stackoverflow.com/questions/1325673/how-to-add-property-to-a-class-dynamically/1333275
    pass

params = Params()
pcct = PrecContChoicTotvotes()
cct = ContChoicTotvotes()


# files
#
pth_current_run = os.getcwd() + '/'

# input from tevs_matcher
#
params.INF_DETAILS = pth_current_run + '../output/details_fuzzy.csv'
params.OUF_PCT_TOTALS = pth_current_run + '../output/precinct_totals.tsv'
params.OUF_CTY_TOTALS = pth_current_run + '../output/county_totals.tsv'
error_cnt = 0
with open(params.INF_DETAILS, 'r') as details_in:
    for line in details_in:
        try:
            dl = Detail_line(line)
        except Exception as e:
            error_cnt += 1
            stderr.write(str(error_cnt) + ' ' +e.__repr__() + '\n')
            continue
        pcct.add(dl.pctid, dl.fuz_contest, dl.fuz_choice, dl.was_voted)
        cct.add(dl.fuz_contest, dl.fuz_choice, dl.was_voted)

with open(params.OUF_PCT_TOTALS, 'w') as ouf:
    ouf.write('Precinct\tContest\tChoice\tVotes\n')
    for key in sorted(pcct.keys()):
        keyparts = key
        s = '\t'.join(keyparts) + '\t'
        s += str(pcct[key]) + '\n'
        ouf.write(s)

with open(params.OUF_CTY_TOTALS, 'w') as ouf:
    ouf.write('Contest\tChoice\tVotes\n')
    for key in sorted(cct.keys()):
        keyparts = key
        s = '\t'.join(keyparts) + '\t'
        s += str(cct[key]) + '\n'
        ouf.write(s)


