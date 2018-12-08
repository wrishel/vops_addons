
"""DetaliLine module for several programs dealing with output from VOPS or output from tevs_matcher.py"""

import sys

class Detail_line(object):
    """A single line created from details.csv and updated before update."""

    def __init__(self, line):
        line = line.replace('\n', '')
        parts = line.split(',')
        parts[-1] = parts[-1].strip()
        if len(parts) < 5:
            sys.stderr.write('skipping short line {}\n'.format(line))
            return

        self.columns = ('file|barcode|contest|choice|was_voted|' +
                        'x6|x7|x8|x9|x10|x11|x12|x13|pctid|' +
                        'fuz_contest|fuz_choice').split('|')
        for i in range(len(parts)):
            self.__setattr__(self.columns[i], parts[i])
        for i in range(i + 1, len(self.columns)):
            self.__setattr__(self.columns[i], None)
        return

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
