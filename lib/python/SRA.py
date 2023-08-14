import logging
import argparse
import sys
import os
import re
import glob

logging.basicConfig(format='%(levelname)s %(asctime)s\t%(message)s', level=logging.INFO)


# create config
def init( options : None) :
    """Create initial config"""
    logger.setLevel(logging.DEBUG)
    # logger.debug("Debugging")
    cfg = None
    if options :
        cfg = options
    return cfg


def read_sequence_dir(dir) :
    """Read sequence dir, collect all fastq files"""

    samples = []

    if dir and os.path.isdir(dir):
        print(glob.glob(dir + "/*.fastq"))
    else:
        logger.error("Missing directory " + str(dir))
    
    return samples

def make_run_file(header=None, data=None, mapping=None, samples=None) :

    print("\t".join(header))
    for row in data:
        print("\t".join(row))

def read_run_template(run_template=None):
    """Read run template file"""

    logger.info("Reading run template " + str(run_template))

    mapping = None
    data = None

    if run_template and os.path.isfile(run_template) :
        with open(run_template) as f :

            found_header_row = False
            # store header information
            header = None
            data   = []
            
            # read until header row - remember headers and position , read data 
            for line in f :
                # print(line)
                columns = line.rstrip().split("\t")

                if not found_header_row :
                    if re.search(columns[0], "sample_name") :
                        header = columns
                        found_header_row = True
                        logger.info("Header with " + str(len(header)) + " columns")
                else :
                    data.append(columns)

            if not found_header_row :
                logger.error("Can not find row with sample_name")

    else:
        logger.error("No file " + str(run_template))

    return (header , data)


def command_line_options():
    """Define and parse command line options"""
    parser = argparse.ArgumentParser(description='Command line options for creating SRA metadata file from template')
  
    parser.add_argument('--template', dest='template', 
                    help='template file for a given run')
    parser.add_argument('--mapping', dest='mapping', 
                    help='mapping file for constants in specified columns')
    parser.add_argument('--sequence-dir', dest='dir', default=None ,
                    help='directory containing sequences/samples to be included in the submission file')
    

    args = parser.parse_args()
    logger.debug(args)
    return args

def main(args) :
    # logger.debug("Debug")
    # logger.info("Info")
    samples = read_sequence_dir(args.dir)

    (header, data) = read_run_template(run_template=args.template)
    make_run_file(header=header, data=data, samples=samples, mapping=None)


if __name__ == '__main__' :
    logger = logging.getLogger(__name__)
    
    args = command_line_options()
  

    cfg = init( options=args)
    logger.debug(args)
    logger.debug("Template:\t" + args.template)

    # logger.setLevel("INFO")
    main(args)