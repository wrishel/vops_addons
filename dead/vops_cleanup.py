"""
vops_cleanup.py -- Build unvoted template for missing files results.

Given a details.csv file in the current folder, this program will
solicit six digit numbers from the user, barcode the file which 
is named with those six digits and a .jpg extension, pull the 
results for the first file with that barcode if one is found,
and append blanked results to additional.csv, with field one
set to the solicited digits + .jpg.

A user must then inspect the image of the missing file and 
modify additions.csv lines, switching 0s to 1s in the fifth field 
(counting from 1) wherever a vote is present. 

additions.csv can then be appended to details.csv

in loop
solicit six digit file number of missing file, or empty to exit.
load missing file with cv2
get barcode using pyzbar
(field numbers from 1)
search details.csv for lines with that barcode in field 2; buffer lines until field 1 changes
convert field 1 of buffered lines to the filename of the missing file,
convert field 5 to 0
convert subsequent fields to 0 or other flag values like 99999
write buffer
"""
import argparse
import pdb
from PIL import Image
from pyzbar import pyzbar
import subprocess
import sys

VALID_LENGTH = 14
ROOTFOLDER = '/media/mitch/Seagate_Backup_Plus_Drive/2018_June'
valid_barcodes_command = "cut -d , -f 2 details.csv | sort | uniq"
import argparse

def parse_command_line():
    parser = argparse.ArgumentParser(
        description='Generate lines to append to details.csv, to be modified by manual inspection of a ballot.'
    )
    parser.add_argument('-i','--image-folder',
                        help="Path to root folder of images, assuming three digit folders containing six digit filenames.jpg."
    )
    return parser.parse_args()


if __name__ == '__main__':
    # run command to get valid_barcodes from details.csv
    args = parse_command_line()
    print "This program requires a details.csv in the current folder,"
    print "and writes to additions.csv in the current folder."
    print "Getting barcodes found in details.csv"
    print "Image folder is ",args.image_folder
    if not args.image_folder:
        print "Specify an image folder on the command line as the -i argument."
        print "For example: python vops_cleanup.py -i /media/mitch/images"
        print "Exiting."
        sys.exit(0)
    task = subprocess.Popen(valid_barcodes_command,
                            shell=True,
                            stdout=subprocess.PIPE)
    valid_barcodes = task.stdout.read()
    assert task.wait() == 0
    
    while True:
        file6 = raw_input("Enter six digit number followed by [Enter], or just [Enter] if done:")
        if type(file6) == type(1):
            file6_str = "%06d" % (file6,)
        else:
            file6_str = file6
        if file6_str == '':
            print 'Exiting normally on no input.'
            sys.exit(0)
        if len(file6_str)<6:
            print "At least six digits needed, and no nondecimal characters."
            continue
        try:
            x = int(file6_str)
        except:
            continue
        image_name = '%s/%s/%s.jpg' % (
            args.image_folder,
            file6_str[0:3],
            file6_str[0:6]
        )
        print "Getting barcode from ",image_name
        im = Image.open(image_name)
        decoded = pyzbar.decode(im)
        barcodes = [d.data for d in decoded if len(d.data)==VALID_LENGTH]
        barcode_string = barcodes[0]
        if barcode_string in valid_barcodes:
            print "Barcode %s is valid, searching details.csv for a file." % (
                barcode_string,)
        else:
            print "Barcode %s not in use, SOL for this file, try again." % (
                barcode_string,)
            continue
        first_file_w_barcode = ''
        template_lines = []
        with open('details.csv','r') as f:
            ctr = 0
            line = f.readline()
            while line:
                fields = line.split(',')
                if int(barcode_string) == int(fields[1]):
                    first_file_w_barcode = fields[0]
                    break
                line = f.readline()
                ctr += 1
            print "Using blanked results of file w barcode, %s" % (
                first_file_w_barcode,
                )
        f.close()
        with open('details.csv','r') as f:
            ctr = 0
            line = f.readline()
            while line:
                fields = line.split(',')
                if first_file_w_barcode == fields[0]:
                    new_line = file6_str
                    new_line += ".jpg"
                    new_line += ","
                    new_line += ",".join(fields[1:4])
                    new_line += ",0 ,-1,-1,-1,-1,-1,0,90.0"
                    template_lines.append(new_line)
                elif template_lines:
                    break
                line = f.readline()
                ctr += 1
        with open('additions.csv','a') as fout:
            fout.write("\n".join(template_lines))
            fout.write("\n")
