"""Maintain a set of contests and choices that represent the 'correct' text for an election.

    Used that set for fuzzy-matching OCR output against the actual names of contest or choices.

    An Election is a collection of Contests. A Contest is a collection of Choices.
    A Choice represents one of the selections on a ballot, such as the candidates
    for Dog Catcher.

    For example in the Election titled "Dogpatch 1954" there could be a Contest named
    "Mayor" with choices "Dan'l Dawgmeat", "Jubilation T. Cornpone Jr", and "Write-in".
"""

__all__ = ['Choice', 'Contest', 'Election', 'preprocess', 'hardmatches']

from fuzzywuzzy import fuzz, process
import re

MIN_MATCH = 57      # minimum acceptable fuzzy match score
MIN_DIFF = 1        # minimum difference between 1st and 2nd match


def preprocess(s):
    """"""
    x = s.upper().strip()               # upper case/strip leading, trailing white space
    x = re.sub(r'[_ -,]+', '', x)       # delete _, space, dash, or comma
    x = re.sub(r'.OTEFOR(ONE|TWO|THREE|FOUR|FIVE)', '', x)
    return x


def _fuzmatch(ocr, possibles, method, preprocessors=[preprocess]):
    """Generic fuzzy match Find the best matching choice in this list.

    Parameters:
        ocr (string):               The OCR-output string to be matched.
        possibles (iterable):       Choice objects to match against ocr.
                                    or any object that answers to .name
        method (function):          A comparision method from fuzzywuzzy.
        preprocessors (iterable):   A list of functions to be called
                                    on the .name attributes of possibles.
    """

    outp = []
    for possible in possibles:
        pos_name = possible.name
        for preprocessor in preprocessors:
            pos_name = preprocessor(pos_name)       # simplify the  name for fuzzy
        pos_size = int(len(pos_name) * 1.1 + 5)
        score = method(ocr[:pos_size], pos_name)
        outval = (score, possible)
        outp.append(outval)

    rvs = list(reversed(sorted(outp)))
    retval = rvs[0][1]
    if len(rvs) >= 2:  # theoretically this must always be true
        best = rvs[0]
        nextbest = rvs[1]
        if best[0] - nextbest[0] < MIN_DIFF or best[0] < MIN_MATCH:
            retval = None  # no clear choice

    elif rvs[0] < MIN_MATCH:
        retval = None  # A one-horse race with no winner

    return retval

class hardmatches(object):

    def __init__(self, input):
        d = dict()
        if input is not None:
            for line in input.readlines():
                columns = [x.strip() for x in line.split('\t')]
                for hardvalue in columns[1:]:
                    d[hardvalue] = columns[0]
        self.d = d

    def match(self, ocr_in):
        return self.d.get(ocr_in, None)


class Choice(object):
    """One of the possible voter choices in a contest."""

    def __init__(self, name):
        self.name = name
        self.matchednames = set()

    def __str__(self):
        return '<Choice: {}>'.format(self.name)

class Contest_Choice(object):
    def __init__(self, contest, choice):
        self.contest = contest
        self.name = choice

    def __str__(self):
        s = '<Contest_Choice '
        s += 'choice: ' + self.choice + '; '
        s += 'contest: ' + self.contest + '>'
        return s



class Contest(object):
    """One of the issues to be decided in an election."""

    def __init__(self, name):
        self.name = name
        self.choices = []

    def add(self, choice):
        """The choice may be a Choice object or an iterable of Choices."""
        if isinstance(choice, Choice):
            self.choices.append(choice)
        else:
            for x in choice:
                self.add(x)

    def fuzmatch(self, ocr):
        """Find the best matching choice in this Contest."""

        retval = _fuzmatch(ocr, self.choices, fuzz.ratio)
        if not retval:
            retval =  _fuzmatch(ocr, self.choices, fuzz.partial_ratio)
            if not retval:
                if re.match(r'[A-Z0-9|\/!] ', ocr):
                    retval = _fuzmatch(ocr[2:], self.choices, fuzz.ratio)
                    if not retval:
                        retval = _fuzmatch(ocr[2:], self.choices, fuzz.partial_ratio)

        return retval

    def __iter__(self):
        """Iterate over the choices"""

        for x in self.choices:
            yield x

    def __str__(self):
        s = '<{}: '.format(self.name)
        s += ', '.join(str(x) for x in self.choices)
        return s + '>'


class Election(object):
    """An entire election: contests each of which have choices."""

    def __init__(self, title=''):
        self.name = title
        self.contests = []
        self.choice_links = dict()

    def add(self, contest):
        """The contest may be a contest object or an iterable of contests."""
        if isinstance(contest, Contest):
            self.contests.append(contest)
        else:
            for x in contest:
                self.add(x)

    def contest(self, name):
        for x in self.contests:
            if x.name == name:
                return x

    def fuzmatch(self, ocr):
        """Find the best matching contest in this election."""

        x = _fuzmatch(ocr, self.contests, fuzz.ratio)
        return x

    def fuzmatch_all_choices(self, ocrchoice):
        """Attempt to find an unambigous contest based on choice only."""

        x = _fuzmatch(ocrchoice, self.choice_links, fuzz.ratio)
        return x

    def load(self, model):
        """Read an entire election from an iterable that contains
           contest \t choice with no duplicates. # signals a comment, which is deleted."""

        with model:
            currcont = None
            for line in model.readlines():
                line = re.sub(r'[ \t]*#.+', '', line)
                line = line.replace(',', '')    # Eliminate all commas in this TSV file
                if len(line) == 1:              # blank line?
                    continue                    # comment-only line
                contest, choice = (x.strip() for x in line.split('\t'))
                if currcont and contest != currcont.name:
                    self.add(currcont)
                    currcont = Contest(contest)
                if not currcont:
                    currcont = Contest(contest)
                currcont.add(Choice(choice))

                # create "cheat list" that enables some contests to be matched base on choice
                #

                curlink = self.choice_links.get(choice, None)
                if curlink:
                    curlink = '**'  # not useful because two contests have the same choice
                else:
                    curlink = Contest_Choice(contest, choice)
                self.choice_links[choice] = curlink

            # Convert self.choice_inks to list and eliminate '**' entreos
            #
            l = []
            for k in self.choice_links.keys():
                v = self.choice_links[k]
                if v != '**':
                    l.append(v)
            self.choice_links = l

            self.add(currcont)

    def __iter__(self):
        """Iterate over the contests"""

        for x in self.contests:
            yield x

    def __str__(self):
        s = '<{}: '.format(self.name)
        s += ', '.join(str(x) for x in self.contests)
        return s + '>'


#         ----------- Module Testing -----------

# test with pytest and test/model_election.py


