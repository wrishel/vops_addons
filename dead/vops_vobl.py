import copy
import logging

class VoteOpBlock:
    """Store a group of results for a contest/choice/ranking."""
    def __init__(self):
        self.x = []
        self.y = []
        self.w = []
        self.h = []
        self.covered = []
        self.marked = []
        self.line_above
        self.contest_text
        self_choice_text

    def shifted(self,x,y):
        retval = copy.deepcopy(self)
        retval.x = [el.x + x for el in self.x] 
        retval.y = [el.y + y for el in self.y] 

    def vprint(self):
        try:
            print(self.contest_text[0:80])
        except UnicodeEncodeError as err:
            print("Unicode encode error in vobl vprint, %s" % (err,))
        for i in range(len(self.x)):
            try:
                print( "M %d x %d y %d w %d h %d cov %d choice %s ltr_rank %s"
                          % (self.marked[i],
                             self.x[i],
                             self.y[i],
                             self.w[i],
                             self.h[i],
                             self.covered[i],
                             self.choice_text,
                             i
                          )
            )
            except UnicodeEncodeError as err:
                print( "Unicode encode error, choice text %s ltr_rank %s" % (err,i))
    
