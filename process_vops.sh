#!/usr/bin/env bash

set -o errexit

datadate=181008

election=ModelElection/data
election2=/Users/Wes/NotForTheCloud/vops/
rpts=/Users/Wes/NotForTheCloud/vops/$datadate

set -o xtrace # show progress by tracing commands

dead/tevs_matcher.py --model 		$election/ElectionModel.txt \
				  --hardmatches $election/hard_matches.tsv \
				  --progress 	100000 \
				  --report \
				  				$rpts/details.csv \
				  				$rpts/details_matched.tsv

# Consolidate details_matched.csv to produce details_consolidate.tsv
#
./consoldt_by_pct.py --progress 100000 \
                     --pct $election2/select___from_t2h_precinct.tsv \
                     $rpts/details_matched.tsv \
                     $rpts/details_consolidate.tsv

# Create 2 spreadsheets comparing consolidated output with old TEVS
# and HARTS:
#				report_both_pct.tsv     -- breakdown by precinct
# 				report_both_overall.tsv -- County wide totals
#
./compare_harts_old_new_tevs.py --harts	  $election2/harts_preprocessed.tsv \
                   				--rptdir  $rpts \
                   				--oldtevs $election2/tevs_public_n_tevs_v_hart_format_9.tsv \
                   						  $rpts/details_consolidate.tsv
