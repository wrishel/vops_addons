"""
    Extract the precinct ID from images.

    Multiple copies of this process may run in parallel to allow
    the use of multiple processors/cores.
"""

import HARTgetBallotType

# global exit_request
# exit_request = False

# signal.signal(signal.SIGINT, exit_gracefully)
# signal.signal(signal.SIGTERM, exit_gracefully)


# -------------------------------------- MAIN --------------------------------------
#
def extract_precinct_from_images():

    with HARTgetBallotType.HARTgetBallotType() as hgbt:
        # log_sleep = True
        # while True:

            file_path = '/Users/Wes/NotForTheCloud/2018_June/unproc/101/101070.jpg'

            ballot_code = hgbt.getBallotType(file_path)
            successful_mode = hgbt.successfulMode
            print('Barcode ={}; Successful Mode={}')\
                .format(ballot_code, successful_mode)




if __name__ == '__main__':
        extract_precinct_from_images()

