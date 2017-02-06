#!/usr/bin/env python

# Generates reverse complements of a column in a delimited table, and appends the reverse
# complement as the last column of the table. 

import sys, os
from string import maketrans
from optparse import OptionParser
import csv

def revc(s):
    t = " " * len(s)
    l=len(s)
    intab = "AaCcGgTt"
    outtab = "TtGgCcAa"
    trantab = maketrans(intab, outtab)
    t=s.translate(trantab)[::-1]
    validchars =  (s.upper().count("A")+ s.upper().count("C")+s.upper().count("T")+s.upper().count("G")+s.upper().count("N"))
    assert validchars == len(s), "Non-ACGTN characters encountered in field '"+ s + "' aborting!"
    return t

if __name__ == '__main__':
    usage  = "usage: %prog [options] <input sequence file>" 
    parser = OptionParser(usage)
    parser.add_option("-c", "--column", dest="column", default=1, help="Sequence column" )
    parser.add_option("-d", "--delimiter", dest="delimiter", default="\t", help="delimiter" )
    parser.add_option("-v", "--verbose", dest="verbose", action="store_true", default=True, help="Verbose [default off]")
    parser.add_option("-s", "--skiplines", dest="skiplines", action="store", type="int", default=0, help="Lines to skip")
  
    (opts, args) = parser.parse_args()
    infile = args[0]
    if not (infile and os.path.isfile(infile) ):
        parser.error("Missing input file"+ infile )

    in_handle  = open(infile)
    out_handle = sys.stdout 
    delimiter = opts.delimiter
    col = int(opts.column) - 1
    n = 0
    reader = csv.reader(in_handle, delimiter=delimiter)
    writer = csv.writer(sys.stdout, delimiter=delimiter)
    for a in reader:
        if n >= opts.skiplines:
            writer.writerow( a + [revc(a[col]) ] )
        else:
            writer.writerow( a ) 
        n = n+1
    in_handle.close()
