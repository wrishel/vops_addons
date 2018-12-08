# Vops Add-Ons
Programs for use with the Trachtenberg Election Verification System (TEVS) downstream from Mitch Trachtenberg's new (in 2018) VOPS program. VOPS takes the raw scanned ballot images and produces an output by analyzing the bar code that identies the ballot type and OCR's values for Candidate and Choice.

Whereas VOPS is meant to be general, applicable to many ballot formats, these programs are meant to be specific, applying to elections run in Humboldt County, California using HARTS equipment.

## Main Programs

These are the main programs in this module. See the source files for command-line parameters.

### tevs_matcher_v2.py 

Receives a details.csv file from VOPS, performs fuzzy matching on that file to produce a new details_fuzzy.csv, where each row is extended by columns to include Contest and choiceChoice. It also looks up the barcode to produce a precinct ID.

fuzzy_report.txt is also produced which identifies values for Contest and Choice that could not be resolved by fuzzy matching and any barcodes that are not identified with a precinct in the election.

### count_votes.py

This uses the output from tevs_matcher_v2 to create a summaries of totals by precinct and for the whole country.

### compare_harts.py

This uses the output from tevs_matcher_v2 to create a summaries of totals by precinct and for the whole country.

### dead

Ignore these files. Someday I will get up the courage to deleting them.



