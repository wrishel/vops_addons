import copy
import logging

class VoteOp:
    """Store a vote op's location + coverage, along with contest/choice text"""
    def __init__(self):
        self.barcode = ''
        self.x = 0
        self.y = 0
        self.w = 0
        self.h = 0
        self.line_above = 0
        self.covered = 0
        self.marked = 0
        self.light = 0
        self.overvoted = 0
        self.undervoted = 0
        self.contest_text = ''
        self.choice_text = ''
        
    def shifted(self,x,y):
        retval = copy.deepcopy(self)
        retval.x = retval.x+x
        retval.y = retval.y+y
        return retval

    def vlog(self):
        """Log vote op"""
        try:
            logging.info(self.contest_text[0:80])
        except UnicodeEncodeError as err:
            logging.error("Unicode encode error, contest text %s" % (err,))
        try:
            logging.info( "M %d x %d y %d w %d h %d cov %d choice %s"
                          % (self.marked,
                             self.x,
                             self.y,
                             self.w,
                             self.h,
                             self.covered,
                             self.choice_text
                          )
            )
        except UnicodeEncodeError as err:
            logging.error( "Unicode encode error, choice text %s" % (err,))
    def vprint(self):
        """Print vote op"""
        try:
            print(self.contest_text[0:80])
        except UnicodeEncodeError as err:
            print("Unicode encode error, contest text %s" % (err,))
        try:
            print( "M %d x %d y %d w %d h %d cov %d choice %s"
                          % (self.marked,
                             self.x,
                             self.y,
                             self.w,
                             self.h,
                             self.covered,
                             self.choice_text
                          )
            )
        except UnicodeEncodeError as err:
            print( "Unicode encode error, choice text %s" % (err,))
                                                        
