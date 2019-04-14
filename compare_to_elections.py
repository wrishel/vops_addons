"""Compare the output from count_votes to the official Elections csv report."""

# This is the version used to deliver reports on Feb 19, 1990

import csv
import os
import re
import sys
stderr = sys.stderr


# Help for dealing with numerics that may be None
#
def plus_or_none(a, b):
    if a is None or b is None:
        return None
    return a + b

def value_or_na(a):
    if a is None:
        return '(na)'
    return a

def minus_or_na(a, b):
    if a is None or b is None:
        return '(na)'
    return a - b

def abs_or_na(a):
    if a is None:
        return '(na)'
    return abs(a)

# classes that define the hierarchy of election objects.
#
#  PrecinctsGroup
#    Precincts
#       Contests
#           Choices
#
class Choice(object):
    '''Summary of counts for a choice within a contest.'''

    def __init__(self, name):
        self.name            = name
        self.votes_elec      = 0
        self.undervotes_elec = 0
        self.votes_cast_elec = 0
        self.overvotes_elec  = 0
        self.votes_tevs      = 0
        self.undervotes_tevs = 0
        self.overvotes_tevs  = 0
        self.votes_cast_tevs = 0

    def add(self, src_choice):
        '''Add the source contest values to this contest.'''
        self.votes_elec       = plus_or_none(self.votes_elec, src_choice.votes_elec)
        self.undervotes_elec  = plus_or_none(self.undervotes_elec , src_choice.undervotes_elec)
        self.votes_cast_elec  = plus_or_none(self.votes_cast_elec , src_choice.votes_cast_elec)
        self.overvotes_elec   = plus_or_none(self.overvotes_elec  , src_choice.overvotes_elec)
        self.votes_tevs       = plus_or_none(self.votes_tevs      , src_choice.votes_tevs)
        self.undervotes_tevs  = plus_or_none(self.undervotes_tevs , src_choice.undervotes_tevs)
        self.overvotes_tevs   = plus_or_none(self.overvotes_tevs  , src_choice.overvotes_tevs)
        self.votes_cast_tevs  = plus_or_none(self.votes_cast_tevs , src_choice.votes_cast_tevs)

    def accumulate_elecs(self, inprowd):
        self.votes_elec += int(inprowd["total_votes"])
        self.undervotes_elec = int(inprowd["total_under_votes"])
        self.overvotes_elec =  int(inprowd["total_over_votes"])
        self.votes_cast_elec = self.votes_elec + self.undervotes_elec + self.overvotes_elec

    def accumulate_tevs(self, inprowd):
        self.votes_tevs += int(inprowd["Votes"])
        self.undervotes_tevs = int(inprowd["Under Votes"])
        self.overvotes_tevs = int(inprowd["Over Votes"])
        self.votes_cast_tevs = self.votes_tevs + self.undervotes_tevs + self.overvotes_tevs


class Contest(object):
    '''The Choices for a contest within a precinct. Includes summary numbers that only
       have meaning at the precinct level such as undervotes and overvotes.'''

    def __init__(self, name):
        self.name = name
        self.choices = dict()

    def get_add(self, src_choice):
        '''Find or create a subordinate choice.'''

        choice = self.choices.get(src_choice.name, Choice(src_choice.name))
        self.choices[src_choice.name] = choice
        return choice


    def accumulate_elecs(self, inprowd):
        choicename = inprowd["candidate_name"]
        choice = self.choices.get(choicename, Choice(choicename))
        choice.accumulate_elecs(inprowd)
        self.choices[choicename] = choice

    def accumulate_tevs(self, inprowd):
        choicename = inprowd["Choice"]
        choice = self.choices.get(choicename, Choice(choicename))
        # stderr.write( '\t'.join(inprowd.values()) + '\n')
        choice.accumulate_tevs(inprowd)
        self.choices[choicename] = choice

    def rollupovrund(self):
        '''Roll up the under and over votes.'''

        for attr in ('undervotes_elec', 'overvotes_elec', 'undervotes_tevs', 'overvotes_tevs' ):
            self._rollupovrund(attr, self.choices.values())

    def _rollupovrund(self, attr_name, choice_list):
        countables = [getattr(x, attr_name) for x in choice_list]
        value = countables[0]
        inconsistent = False
        for othervalue in countables[1:]:
            try:
                assert value == othervalue
            except AssertionError as e:
                print 'AssertionError {} in {} in {}, attr={}'\
                    .format(othervalue, countables, self.name, attr_name)
                inconsistent = True

        if inconsistent:
            for choice in choice_list:
                setattr(choice, attr_name, None)
        else:
            for choice in choice_list:
                setattr(choice, attr_name, value)



class Precinct(object):
    def __init__(self, name):
        self.name = name
        self.contests = dict()

    def accept_contest(self, src_contest):
        '''Retreive or add the contest that corresponds to src_contest and return the object.'''
        
        new_contest = self.contests.get(src_contest.name, Contest(src_contest.name))
        self.contests[src_contest.name] = new_contest
        return new_contest


        # for src_choice in src_contest.choices.values():
        #     added_contest = self.contests.get(src_contest_name, Contest(src_contest_name))
        #     added_contest.accept_choice()
        # 
        #     #
        #     choice = self.choices.get(choicename, Choice(choicename))
        #     src_choice_name = choice.name


    def accumulate_elecs(self, inprowd):
        contname = inprowd["Contest_title"]
        contest = self.contests.get(contname, Contest(contname))
        contest.accumulate_elecs(inprowd)
        self.contests[contname] = contest

    def accumulate_tevs(self, inprowd):
        contname = inprowd["Contest"]
        contest = self.contests.get(contname, Contest(contname))
        contest.accumulate_tevs(inprowd)
        self.contests[contname] = contest

    def rollupovrund(self):
        '''Roll up the under and over votes'''

        for contest in self.contests.values():
            print 'rolling up ' + contest.name + ' in ' + self.name
            contest.rollupovrund()


class PrecinctsGroup():
    '''A precinct or the entire election.'''

    def __init__(self):
        self.precincts = dict()

    def accumulate_elecs(self, inprowd):
        '''Accumulate data from HARTS in a precinct, creating it if necessary. inprowd is a
           a csv input row as a dict'''

        pctname = inprowd["Precinct_name"]
        pct = self.precincts.get(pctname, Precinct(pctname))
        pct.accumulate_elecs(inprowd)
        self.precincts[pctname] = pct

    def accumulate_tevs(self, inprowd):
        '''Accumulate data from tevsin a precinct, creating it if necessary. inprowd is a
           a csv input row as a dict'''

        pctname = inprowd["Precinct"]
        pct = self.precincts.get(pctname, Precinct(pctname))
        pct.accumulate_tevs(inprowd)
        self.precincts[pctname] = pct

    def rollupovrund(self):
        '''Roll up the under and over votes'''

        for precinct in self.precincts.values():
            print 'rolling up ' + precinct.name + ' in Precincts.Group'
            precinct.rollupovrund()


# Support for setting up runtime parameters
#
class Params(object):   # https://stackoverflow.com/questions/1325673/how-to-add-property-to-a-class-dynamically/1333275
    pass

def insert_run_number(pth, base_file_name):
    # assert 'NN' in base_file_name
    return os.path.join(pth, base_file_name).replace('NN', params.FILE_NAME_SUFFIX)


# ---------------------------------------   MAIN   ---------------------------------------

params = Params()

# files
#
params.FILE_NAME_SUFFIX = '16'
pth_current_run = os.getcwd() + '/'
pth_elections = pth_current_run + 'data/static_2018_nov/from_elections/'

# files
#
params.INF_ELECTIONS = insert_run_number(pth_current_run,
                                    'data/static_2018_nov/from_elections/2018NovElectionFinal.csv')
params.INF_PCT_TOTALS = insert_run_number(pth_current_run, 'output/precinct_totalsNN.tsv')
params.OUF_PCT_COMPARED = insert_run_number(pth_current_run, 'output/precinct_comparedNN.tsv')
params.OUF_CNTY_COMPARED = insert_run_number(pth_current_run, 'output/county_comparedNN.tsv')

# INF_ELECTIONS Column names being used:
#
#   "Precinct_name", "Contest_title", "candidate_name", "total_ballots",
#   "total_votes", "total_over_votes", "total_under_votes"

# INF_PCT_TOTALS column names being used:
#
# "Precinct", "Contest", "Choice", "Votes", "Over Votes", "Under Votes"

# OUF_PCT_COMPARED column names being used:
#
params.OUF_PCT_COLUMNS = \
    (
        "Precinct",
        "Contest",
        "Choice",

        "Elec Votes",
        "Elec Over Votes",
        "Elec Under Votes",
        "Elec Cast Votes",

        "TEVS Votes",
        "TEVS Over Votes",
        "TEVS Under Votes",
        "TEVS Cast Votes",

        "Votes: Elec - TEVS",
        'Over votes: Elec - TEVS',
        'Under votes: Elec - TEVS',
        'Cast votes: Elec - TEVS',
        'Votes: abs( Elec - TEVS)'
    )

params.OUF_CNTY_COLUMNS = \
    ("Contest",
     "Choice",

     "Elec Votes",
     "Elec Over Votes",
     "Elec Under Votes",
     "Elec Cast Votes",

     "TEVS Votes",
     "TEVS Over Votes",
     "TEVS Under Votes",
     "TEVS Cast Votes",

     "Votes: Elec - TEVS",
     'Over votes: Elec - TEVS',
     'Under votes: Elec - TEVS',
     'Cast votes: Elec - TEVS',
     'Votes: abs( Elec - TEVS)')

# run control for debugging
#
params.SHORT_RUN = None  # for debugging, read only this many input lines

# HACKS:
#
#	Hacks on input from TEVS
#
#		1. The elections data file (csv) does not include the VOTE FOR notation with
#		the candidate name, so we eliminate this from tevs. A more useful hack
#		would be to look them up in elections.txt.
#
#       2. HARTS distinguishes between unqualified and qualified write-ins while
#       VOPS cannot. Since the Nov 2018 election had no qualified write-ins
#       we change 'Unqualified Write-Ins' from Elections to 'WRITEIN' and we
#       eliminate 'Unresolved WriteIns' from the output altogether.
#
#       3. HARTS sends hyphens in candidate names while VOPS sends them
#       intermittenly. So we delete hypends from both to ensure a
#       match.
#
#	Hacks on input from Elections
#
#		1. Elections data includes embedded commas within the CSV. We exclude
#		commas coming out of VOPS to avoid problems because VOPS does not
#		implement the CSV specifications for embedded commas. So we exclude
#		commas from the Elections input.
#
#		2. The elections data file does not include the titles of
#		(most or all?) propositions and measures, although for
#		measures it does include the jurisdiction (apparently no
#		jurisdiction is used for all-county measures. For now we lop
#		off anything after any item in loppables, below. A more useful
#		hack would be to look them up in elections.txt.
#
#		3. The elections data file includes quote marks around
#		nicknames but we have surpressed those in the vops data. So we
#		remove them from the elections file.
#
#		4. The elections data file includes hypens in hypenated names
#		but we have surpressed those in the vops data. So we
#		remove them from the elections file.
#
#		5. The elections data file includes parens around the term length
#		-- e.g., FERNDALE CITY COUNCILMEMBER (4YR) -- but they are not
#		coming from VOPS or we have surpressed them. But there are
#       other situations where the parens come in from vops
#       but not from elections. So we eliminate parens from both
#       versions.

#       6. HARTS sends hyphens in candidate names while VOPS sends them
#       intermittenly. So we delete hypends from both to ensure a
#       match.
#
#
#	Output hacks.
#
#		Excel cannot accept certain precinct IDs (such as 1E-36) as anything but
#		a floating point number. We prefix "'  " on each precinct ID to avoid this.

loppables = [
	"MEASURE I", # CITY OF EUREKA",
	"MEASURE J", # CITY OF RIO DELL",
	"MEASURE K",
	"MEASURE L",# CUTTEN SCHOOL DISTRICT",
	"MEASURE M", # CITY OF ARCATA",
	"MEASURE N", # NORTHERN HUMBOLDT UNION HIGH SCHOOL DISTRICT",
	"MEASURE O", # HUMBOLDT COUNTY PUBLIC SAFETY/ESSENTIAL SERVICES RENEWAL"
]

candidate_matches = None # ['GAVIN', 'JOHN H']
assertion_failures = dict()

election_by_pct = PrecinctsGroup()
print 'Precinct comparison output: ' + params.OUF_PCT_COMPARED
print 'County comparison output: ' + params.OUF_CNTY_COMPARED
print 'Elections input: ' + params.INF_ELECTIONS


with open(params.INF_ELECTIONS) as elecs_in:
    elec_dict = csv.DictReader(elecs_in)
    for line in elec_dict:
        contest = line['Contest_title']
        contest = contest.replace(',', '')
        contest = contest.replace('(', '')
        contest = contest.replace(')', '')
        for contest_title in loppables:
            if contest.startswith(contest_title):
                contest = contest_title
        line['Contest_title'] = contest

        choice = line["candidate_name"]

        # >>>>>>>>>  FIX FOR NOVEMBER 2018 ONLY  <<<<<<<<<<
        #
        if 'Unresolved Write-Ins' in choice: # choice == 'Unresolved WriteIns':
            continue

        choice = choice.replace('Unqualified Write-Ins', 'WRITEIN')
        choice = choice.replace('"','')
        choice = choice.replace('-','')
        choice = choice.replace(',','')
        line["candidate_name"] = choice
        if candidate_matches:
            debugging_ok = False
            for cm in candidate_matches:
                if choice.startswith(cm):
                    debugging_ok = True
        else:
            debugging_ok = True     # not debugging, so all values pass

        if debugging_ok:
            election_by_pct.accumulate_elecs(line)

print 'TEVS input: ' + params.INF_PCT_TOTALS


with open(params.INF_PCT_TOTALS) as tevs_in:
    tevs_dict = csv.DictReader(tevs_in, delimiter='\t')
    for line in tevs_dict:
        contest = line['Contest']
        contest = re.sub(r' VOTE FOR .+', '', contest)
        contest = re.sub(r'(MEASURE [A-Z]).+', r'\1', contest)
        contest = re.sub(r'(PROPOSITION \d+).*', r'\1', contest)
        contest = contest.replace('(', '')
        contest = contest.replace(')', '')
        line['Contest'] = contest

        choice = line['Choice']
        choice = choice.replace('-','')
        line['Choice'] = choice
        election_by_pct.accumulate_tevs(line)

print '\n--------------------Roll up by precinct'
election_by_pct.rollupovrund()

with open(params.OUF_PCT_COMPARED, 'w') as precincts_out:
    precincts_out.write('\t'.join(params.OUF_PCT_COLUMNS) + '\n')
    comp_writer =  csv.writer(precincts_out, delimiter='\t')
    for keyp in sorted(election_by_pct.precincts.keys()):
        precinct = election_by_pct.precincts[keyp]
        for keycon in sorted(precinct.contests.keys()):
           contest = precinct.contests[keycon]
           for keych in sorted(contest.choices.keys()):
                choice = contest.choices[keych]
                outrow = (
                    "'  " + precinct.name,
                    contest.name,
                    choice.name,

                    choice.votes_elec,
                    choice.overvotes_elec,
                    choice.undervotes_elec,
                    choice.votes_cast_elec,

                    value_or_na(choice.votes_tevs),
                    value_or_na(choice.overvotes_tevs),
                    value_or_na(choice.undervotes_tevs),
                    value_or_na(choice.votes_cast_tevs),

                    choice.votes_elec - choice.votes_tevs,
                    "(na)" if choice.overvotes_elec is None or choice.overvotes_tevs is None else
                        choice.overvotes_elec - choice.overvotes_tevs,
                    "(na)"  if choice.undervotes_tevs is None or choice.undervotes_elec is None else
                        choice.undervotes_elec - choice.undervotes_tevs,
                    minus_or_na(choice.votes_cast_elec, choice.votes_cast_tevs),
                    abs(choice.votes_elec - choice.votes_tevs))
                comp_writer.writerow(outrow)

county = Precinct('Humboldt County')
print '\n--------------------Roll up the county'


# create a new tree for the county-wide election, i.e., the country is a single "precinct"
#
for src_precinct in election_by_pct.precincts.values():
    for src_contest in src_precinct.contests.values():
        new_contest = county.accept_contest(src_contest) # add/accumulate a contest into county
        for src_choice in src_contest.choices.values():
            new_choice = new_contest.get_add(Choice(src_choice.name))
            new_choice.add(src_choice)


# write the county-wide comparison
#
with open(params.OUF_CNTY_COMPARED, 'w') as precincts_out:
    comp_writer =  csv.writer(precincts_out, delimiter='\t')
    precincts_out.write('\t'.join(params.OUF_CNTY_COLUMNS) + '\n')
    for keycon in sorted(county.contests.keys()):
        contest = county.contests[keycon]
        for keych in sorted(contest.choices.keys()):
            choice = contest.choices[keych]
            outrow = (contest.name,
                      choice.name,

                      choice.votes_elec,
                      choice.overvotes_elec,
                      choice.undervotes_elec,
                      choice.votes_cast_elec,

                      value_or_na(choice.votes_tevs),
                      value_or_na(choice.overvotes_tevs),
                      value_or_na(choice.undervotes_tevs),
                      value_or_na(choice.votes_cast_tevs),

                      minus_or_na(choice.votes_elec, choice.votes_tevs),
                      minus_or_na(choice.overvotes_elec, choice.overvotes_tevs),
                      minus_or_na(choice.undervotes_elec, choice.undervotes_tevs),
                      minus_or_na(choice.votes_cast_elec, choice.votes_cast_tevs),
                      abs(choice.votes_elec - choice.votes_tevs) \
                          if choice.votes_elec is not None and choice.votes_tevs is not None\
                          else '(n/a)'
                     )
            comp_writer.writerow(outrow)
            # if choice.votes_elec  * choice.votes_tevs == 0:
            #     if max(choice.votes_elec, choice.votes_tevs) > 50:
            #         stderr.write('\t'.join((str(x) for x in outrow)) + '\n')
