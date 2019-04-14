"""
Global constants for ETP Running Precinct Counts (etpruncnt2.1)
"""

import platform
import os

def ppath(*args):
    return os.path.join(PROJ_PATH, *args)

def nfcpath(*args):
    return os.path.join(nfc, *args)



# Some testing routines find test data based on the path to the root of
# the project. This is a hack to find it. If the name of the project root directory
# changes it must be updated in projname. If the name of the root of the project
# directory is repeated in the path to the project directory this will fail.
#
projname = 'etpruncnt2.1'
thisfilepath = os.path.dirname(os.path.realpath(__file__))
x = thisfilepath.find(projname)
if x < 0:
    raise Exception('projname ({}) not in the path to this source file ({})' \
                    .format(projname, thisfilepath))
x = x + len(projname) + 1
if thisfilepath[x:].find(projname) > -1:
    raise Exception('projname ({}) is repeated in the path to this source file ({})' \
                    .format(projname, thisfilepath))
PROJ_PATH = thisfilepath[:x]

DONT_PROCESS_ABOVE = '243549.jpg'  # if this is less than 6 digits use leading zeroes

TEVS_OPS = '/home/tevs/tevs_ops'

# PATH_TO_IMAGES = '/Users/Wes/NotForTheCloud/etprunct_test/input'
# PATH_TO_IMAGES = ppath('testing', 'HARTgetBallotTypeTest')
# PATH_TO_IMAGES = '/media/sf_2016-11/images'
# PATH_TO_IMAGES = '/Users/Wes/NotForTheCloud/2017_Nov/imgByPct'
# PATH_TO_IMAGES = '/Volumes/Seagate_Backup_Plus_Drive/2016-11/images'
PATH_TO_IMAGES = os.path.join(TEVS_OPS, 'processed')

IMAGE_FILE_NAME_PATTERN = ['*.jpg']

IMG_extract_id = lambda ballotNum : ballotNum[1:7]  # callable to extract the ballot ID from the margin string

# at least on some ballots, this field is the page number (2 pages per sheet)
# The caller converts this to the sheet number if needed. Pages 1 and 2 on sheet 1, etc.
#
# THIS IS CONFUSING BECAUSE BALLOT WORKERS USE THE WORD "PAGE" TO REFER TO SHEETS. PAGE 1 HAS SIDE 1 AND SIDE 2
#
IMG_extract_page_num = lambda ballotNum : int(ballotNum[8])

def IMG_OK_to_process(file_path):
    return os.path.basename(file_path) <= DONT_PROCESS_ABOVE


# Currently we run certain files out of /User/Wes/NotForTheCloud. The path
# to that directory varies depending on whether we're on the Mac host or
# Ubuntu on a virtual box.
#
platf = 'mac' if 'Darwin' in platform.platform(terse=1) else 'ubu'
nfcbase = '/media/sf_Wes' if platf == 'ubu' else '/Users/Wes'

nfc = os.path.join(nfcbase, 'NotForTheCloud/etprunct_test')

# on a production system the equivalent of NFC is on the computer's disk
#
# nfc = TEVS_OPS

PATH_TO_DB =  os.path.join(nfc, 'output', 'precinctTracker.db')
PATH_TO_LOG = os.path.join(nfc, 'output')

del platf, nfcbase, nfc  # keep this nasty platform stuff on the down-low

DB_IMG_PCT_ID_RESERVED  = '__RESERVED__' # image file is currently being processed
DB_IMG_PCT_ID_UNKNOWN   = '__???__'  # value for undetermined precinct

# Precinct map for Nov 2017 election
#
PRECINCT_MAP = {
    '000001': '1CS-1', '000002': '1CS-4', '000003': '1E-36', '000004': '1E-45',
    '000005': '1E-55', '000006': '1ES-1', '000007': '1F--1', '000008': '1F--7',
    '000009': '1FS',   '000010': '1FS-1', '000011': '1FS-4', '000012': '1FS-9',
    '000013': '1FSF',  '000014': '1LU',   '000016': '1MU',   '000017': '1MUF',
    '000018': '1RV-2', '000019': '1SB-1', '000020': '1SB-4', '000021': '1SB12',
    '000022': '1SB14', '000023': '1SU',   '000024': '2CU',   '000025': '2F--2',
    '000026': '2F--3', '000027': '2F-R1', '000028': '2F-R3', '000029': '2F-R4',
    '000030': '2HV-1', '000031': '2R--1', '000032': '2RV-1', '000033': '2SHR1',
    '000034': '2SHR2', '000035': '3B--1', '000036': '3BLF',  '000037': '4E-15',
    '000038': '4E-52', '000039': '4PEF',  '000040': '5BLF',  '000041': '5KT-2',
}


# Precinct map for Nov 2016 election

PRECINCT_MAP = {
'000001': '1CS-1', '000002': '1CS-2', '000003': '1CS-3', '000004': '1CS-4',
'000005': '1E-36', '000006': '1E-43', '000007': '1E-45', '000008': '1E-55',
'000009': '1E-59', '000010': '1ES-1', '000011': '1F--1', '000012': '1F--7',
'000013': '1FS',   '000014': '1FS-1', '000015': '1FS-4', '000016': '1FS-9',
'000017': '1LU',   '000018': '1MU',   '000019': '1MUF',  '000020': '1RV-2',
'000021': '1SB-1', '000022': '1SB-4', '000023': '1SB10', '000024': '1SB12',
'000025': '1SU',   '000026': '2BV-1', '000027': '2CU',   '000028': '2F--2',
'000029': '2F--3', '000030': '2F--4', '000031': '2F-R1', '000032': '2F-R2',
'000033': '2F-R3', '000034': '2F-R4', '000035': '2HV-1', '000036': '2MR',
'000037': '2R--1', '000038': '2R--2', '000039': '2RV-1', '000040': '2SH-1',
'000041': '2SH-2', '000042': '2SH-3', '000043': '2SH-4', '000044': '2SH-5',
'000045': '2SH-7', '000046': '2SH-8', '000047': '2SHF1', '000048': '2SHR1',
'000049': '2SHR2', '000050': '2SHS4', '000051': '2SHS7', '000052': '2SHVF',
'000053': '3A--1', '000054': '3A--2', '000055': '3A--3', '000056': '3A--4',
'000057': '3A--7', '000058': '3A--9', '000059': '3A-10', '000060': '3A-11',
'000061': '3A-12', '000062': '3A-13', '000063': '3A-J1', '000064': '3A-P2',
'000065': '3A-P4', '000066': '3AS-1', '000067': '3AS-9', '000068': '3B--1',
'000071': '3ES-6', '000072': '3FW',   '000073': '3JCFR', '000074': '3JCFR', '000075': '3JCWR',
'000076': '3KL',   '000077': '3KL-1', '000078': '3MA-1', '000079': '3PA-1',
'000080': '3PESF', '000081': '4E-11', '000082': '4E-12', '000083': '4E-13',
'000084': '4E-14', '000085': '4E-21', '000086': '4E-22', '000087': '4E-23',
'000088': '4E-24', '000089': '4E-25', '000091': '4E-31', '000092': '4E-32',
'000093': '4E-33', '000094': '4E-34', '000095': '4E-51', '000096': '4E-52',
'000097': '4E-54', '000098': '4ES-4', '000099': '4ES-5', '000100': '4ES-6',
'000101': '4PEF',  '000102': '5AS-4', '000103': '5BL',   '000104': '5FB',
'000105': '5GP',   '000106': '5KT-1', '000107': '5KT-3', '000108': '5KT-4',
'000109': '5KT-6', '000110': '5KTS3', '000111': '5MC',   '000112': '5MK-1',
'000113': '5MK-2', '000114': '5MK-3', '000115': '5MK-4', '000116': '5MK-4A',
'000117': '5MK-5', '000118': '5MK-5A','000119': '5MK-6', '000120': '5MK-6A',
'000121': '5MK-7', '000122': '5MK-8', '000123': '5OR',   '000124': '5PA-3',
'000125': '5T--1', '000126': '5TU-1', '000127': '5TU-4'
}
