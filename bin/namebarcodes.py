#!/usr/bin/env python
# Script to take a histobram of six-character barcodes and
# identify the barcodes by name.

#  2013-10-07 first draft 
#  2013-10-21 first deployment
#  2014-02-26 modified to tolerate double (Nextera) barcodes

BARCODES = {
"ATCACG" : "TruSeqIndex01",
"CGATGT" : "TruSeqIndex02",
"TTAGGC" : "TruSeqIndex03",
"TGACCA" : "TruSeqIndex04",
"ACAGTG" : "TruSeqIndex05",
"GCCAAT" : "TruSeqIndex06",
"CAGATC" : "TruSeqIndex07",
"ACTTGA" : "TruSeqIndex08",
"GATCAG" : "TruSeqIndex09",
"TAGCTT" : "TruSeqIndex10",
"GGCTAC" : "TruSeqIndex11",
"CTTGTA" : "TruSeqIndex12",
"AGTCAA" : "TruSeqIndex13",
"AGTTCC" : "TruSeqIndex14",
"ATGTCA" : "TruSeqIndex15",
"CCGTCC" : "TruSeqIndex16",
"GTCCGC" : "TruSeqIndex18",
"GTGAAA" : "TruSeqIndex19",
"GTGGCC" : "TruSeqIndex20",
"GTTTCG" : "TruSeqIndex21",
"CGTACG" : "TruSeqIndex22",
"GAGTGG" : "TruSeqIndex23",
"ACTGAT" : "TruSeqIndex25",
"ATTCCT" : "TruSeqIndex27",
"TAAGGCGA" : "Nextera-N701",
"CGTACTAG" : "Nextera-N702",
"AGGCAGAA" : "Nextera-N703",
"TCCTGAGC" : "Nextera-N704",
"GGACTCCT" : "Nextera-N705",
"TAGGCATG" : "Nextera-N706",
"CTCTCTAC" : "Nextera-N707",
"CAGAGAGG" : "Nextera-N708",
"GCTACGCT" : "Nextera-N709",
"CGAGGCTG" : "Nextera-N710",
"AAGAGGCA" : "Nextera-N711",
"GTAGAGGA" : "Nextera-N712",
"TAGATCGC" : "Nextera-N501",
"CTCTCTAT" : "Nextera-N502",
"TATCCTCT" : "Nextera-N503",
"AGAGTAGA" : "Nextera-N504",
"GTAAGGAG" : "Nextera-N505",
"ACTGCATA" : "Nextera-N506",
"AAGGAGTA" : "Nextera-N507",
"CTAAGCCT" : "Nextera-N508",
}
DOUBLE = {}
for k, v in BARCODES.items():
    if v[-3] == "7":
        for k2, v2 in BARCODES.items():
            if v2[-3] == "5":
                DOUBLE[k+k2] = v[-4:] + "-" + v2[-4:]

for k, v in DOUBLE.items():
    BARCODES[k] = v

# LOOKUP = {v:k for k, v in BARCODES.items()}
LOOKUP = {}
for k,v in BARCODES.items():
    LOOKUP[v] = k

Barcodenames = BARCODES.values()

Barcodecounts = {}
Barcodecounts[""] = 0

for k in Barcodenames:
    Barcodecounts[k] = 0
    Barcodecounts[k+".ERROR"] = 0

def neighbors(kmer):
    ''' Returns a list of Hamming-distance 1 ngiehbors to a string kmer'''
    neighborlist = []
    kmer = kmer.rstrip()
    for i in range(0, len(kmer.rstrip())):
        for j in ["A", "C", "G", "T", "N"]:
            if j == kmer[i].upper():
                continue    #  The kmer itself is not among its neighbors
            q = kmer[0:i] + j + kmer[i+1:]
            neighborlist.append(q)
    return neighborlist

def barcodeerror(Barcodedict):
    ''' Augments Barcodedict with additional entries representing one-off errors'''
    for k in Barcodedict.keys():
        errorlist = neighbors(k)
        for error in errorlist:
            Barcodedict[error] = BARCODES[k]+ ".ERROR"

import sys, os
from optparse import OptionParser

if __name__ == '__main__':
    usage = "usage: cat barcodes.csv | namebarcodes.py "
    parser = OptionParser(usage)
    parser.add_option("-d", "--detail", dest="detail", action="store_true", default=False, help="Detailed output")
    parser.add_option("-e", "--endonly", dest="endonly", action="store_true", default=False, help="Search Nextera-first 8bp only")
    parser.add_option("-b", "--beginonly", dest="beginonly", action="store_true", default=False, help="Search Nextera-first 8bp only")
    parser.add_option("-t", "--truseqonly", dest="truseqonly", action="store_true", default=False, help="Search Truseq-first 6bp only")

    (opts, args) = parser.parse_args()

    Barcodehistogram = {}
    total = 0
    barcodeerror(BARCODES)
    for line in sys.stdin:
        s = line.strip().split()
        bc = s[0]
        if opts.beginonly:
            bc = bc[0:8]
        elif opts.endonly:
            bc = bc[8:]
        elif opts.truseqonly:
            bc = bc[0:6]
        N = len(bc)
        try:
            ct = int(s[1])
        except IndexError:
            ct = 1
        Barcodehistogram[bc] = ct
        total += ct
        try:
            Barcodecounts[BARCODES[bc]] += ct
        except KeyError:
            Barcodecounts[""] += ct
    numberjunk = Barcodecounts[""]

    if opts.detail:
        for k, v in sorted(Barcodehistogram.items(), key=lambda x: x[1]):
            a = ""
            try:
                a = BARCODES[k]
            except KeyError:
                pass
            print "%s\t% 12d\t%f\t%s" % (k, int(v), (float(v) / total), a)
        print "Total\t% 12d" % (total)
        print "Junk\t% 12d\t%f" % (numberjunk, float(numberjunk) / total)
    else:
        print "#Index      \t      perfect\tone mismatch\tfrac. perfect\tone mismatch\tsum"
        for bcn in sorted(Barcodenames):
            n_perfect = Barcodecounts[bcn]
            n_errors = Barcodecounts[bcn + ".ERROR"]
            if len(LOOKUP[bcn]) == N:
                print "%s\t% 12d\t% 12d\t%f\t%f\t%f" % (bcn, n_perfect, n_errors, float(n_perfect) / total, float(n_errors) / total, float(n_perfect + n_errors) / total)
        print "%s\t% 12d\t            \t%f" % ("Junk       ", numberjunk, float(numberjunk) / total)
        print "%s\t% 12d"  % ("Total        ", total)
