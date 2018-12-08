import logging

class BallotImageSet:
    """A managed dictionary, keyed on barcode, with arrays of BallotImages"""

    def __init__(self,cli_args):
        self.d = {}
        self.found_median_bi = {}
        self.counts_dict = {}
        self.marks_dict = {}
        self.image_dict = {}
        self.args = cli_args
        self.coverage_threshold = cli_args.coverage_threshold
        self.unprocessed = []
        self.unprocessed_barcode = []

    def add(self,barcode,bi):
        """Add a new BallotImage to the correct array for the barcode
        until it reaches a length of twelve, then no-op.
        Only the first eight instances of a barcode might find use
        in reconciliation, so later instances can be safely discarded.
        """
        if barcode not in self.d:
            self.d[barcode]=[]
            self.counts_dict[barcode]=0
        count = len(self.d[barcode])
        if count<=13:
            if len(self.d[barcode])>1:
                #print self.d[barcode][-1].filename
                #print bi.filename
                if self.d[barcode][-1].filename != bi.filename:
                    self.d[barcode].append(bi)
                else:
                    print "Already added",bi.filename
            else:
                #print "Adding 0th",bi.filename
                self.d[barcode].append(bi)
        self.counts_dict[barcode] = self.counts_dict[barcode]+1

    def insert_at_front(self,barcode,bi):
        """Add a new BallotImage to the front of the correct array"""
        print 'Why are we at insert_at_front?'
        print barcode, bi.filename
        return self.add(barcode,bi)
        """
        nominal_width_of_vop = self.args.nominal_width_of_vop
        nominal_height_of_vop = self.args.nominal_height_of_vop
        if barcode not in self.d:
            self.d[barcode]=[]
            self.counts_dict[barcode]=0
        print "Adding reference ballot image for barcode",barcode
        # clean up vote array
        bi.correct_reference_va()
        self.d[barcode].insert(0,bi)
        self.counts_dict[barcode] = self.counts_dict[barcode]+1
        self.found_median_bi[barcode]=1
        """
