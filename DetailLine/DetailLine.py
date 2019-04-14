
"""DetaliLine module for several programs dealing with output from VOPS or output from tevs_matcher.py"""

import sys

class Detail_line(object):
    """A single line created in the form of VOPS's details.csv including additional
       fields for fuzzy_details. Input can be in the form of a comma-separated string
       or a row object from csv.reader()"""

    def __init__(self, line):
        if isinstance(line, basestring):    # is line a str?
            line = line.replace('\n', '')
            parts = line.split(',')
            parts[-1] = parts[-1].strip()

        else: # line must be a row object
            parts = line

        if len(parts) < 5:
            sys.stderr.write('skipping short line {}\n'.format(line))
            return

        self.columns = ('file|barcode|contest|choice|initial_voted|' +
                        'darkened_px_cnt|ulc_x|ulc_y|width|height|' +
                        'initial_overvoted|mode_darkend_pxs|rotation|pctid|' +
                        'fuz_contest|fuz_choice|corrected_barcode|'
                        'undervoted').split('|')

        # VOPS fields numbered from 1           dl attribute name
        # ----------------------------          ------------------
            #  1    image file name                 file
            #  2    barcode                         barcode
            #  3    contest                         contest text
            #  4    choice                          choice text
            #  5    initial opinion on voted        initial_voted
            #  6    darkened pixel count            darkened_px_cnt
            #  7-10 x,y,w,h coords (possibly
            #        after rotation)
            #                                       ulc_x, ulc_y, width, height
            # 11 initial opinion on overvoted       initial_overvoted,
            # 12 mode used to collect darkened pixels
            #                                       mode_darkend_pxs
            #  1 = adjusted template coords were used,
            #  0 = conncomp blobs used because OK
            # 13 image was rotated through float degrees
            #                                      rotation

            # fields added here
            # ------------------
            # 14  precinct ID                       pctid
            # 15  contest namd as corrected         fuz_contest
            # 16  choice as corrected               fuz_choice
            # 17  corrected barcode                 corrected_barcode
            # 18  undervoted                        undervoted

        # construct the DetailLine object by creating named attributes
        #
        for i in range(len(parts)):
            self.__setattr__(self.columns[i], parts[i])
        for i in range(i + 1, len(self.columns)):
            self.__setattr__(self.columns[i], None)

    def _assemble(self):
        """Return a list of items in order"""


        # assemble the items and return (column_name, column_value)
        #
        items = []
        for col in self.columns:
            value = self.__getattribute__(col)
            items.append((col, value))

        return items

    def __str__(self):
        cols = self._assemble()
        s = '<dl '
        items = []
        for colname, colvalue in cols:
            ss = colname
            ss += ': '
            ss += str(colvalue)
            items.append(ss)

        s += ('; ').join(items)
        s += '>'
        return s

    def output(self):
        """Return a csv string like the input file.
           Does not handle embedded quotes properly!"""

        out_items = self._assemble()
        out_itemss = [str(x[1]) for x in out_items]
        s = ','.join(out_itemss)
        return s + '\n'

    def aslist(self):
        '''Return the elements as a list in the order established by _assemble()'''

        l = []
        for item in self._assemble():
            l.append(item[1])

        return l

    def parts_tuple(self, items):
        '''Return a tuple made of the parts named in items.'''

        l = []
        for item in items:
            if item not in self.columns:
                raise ValueError(item + ' not a column name')

            l.append(self.__getattribute__(item))

        return tuple(l)