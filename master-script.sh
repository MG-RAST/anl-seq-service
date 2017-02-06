#!/bin/bash
# MASTER SCRIPT FOR ANL Sequencing core

#defaults
THREADS=8

# set option
HELP=0
INPUT=''
OUTPUT=''


usage () { 
	echo "Usage: anl_seq_core.sh [-h <help> -p <proxy mode off>] -i <input directory> -a <output directory> -s <samplesheet> "

	echo "[-e] Missing eamss files"
	echo "[-m] allow 1 mismatch" 
	echo "[-t <tile_name>] process only the tile named <tile_name> e.g. -t s_1"
	echo "[-x] Missing stats files"
	echo "[-b] Missing bcl file"
	echo "<INPUT DIR> -- the path to the input files"
 	echo "<OUTPUT DIR> -- the path to the output files"
	echo "<SAMPLE SHEET> -- path to the sample sheet (xls format)"
 }

# get options
while getopts bxmhe:i:o:s:t: option; do
    case "${option}"
        in
            h) 	HELP=1;;
            i) 	INPUT=${OPTARG};;
            o) 	OUTPUT=${OPTARG};;
			e) 	OPTIONS="${OPTIONS}	--no-eamss"
			m) 	OPTIONS="${OPTIONS} --mismatches 1"
			t)	OPTIONS="${OPTIONS} -t ${OPTARG}"
			x) 	OPTIONS="${OPTIONS} --ignore-missing-stats"
			b)  OPTIONS="${OPTIONS} --ignore-missing-bcl"
			s) 	SAMPLESHEET=${OPTARG};;
		*)
			usage
			;;
    esac
done

#Trimming the adaptors < WHAT IS STORY BEHIND THE ADAPTER DIR?>
# this needs a global dir with all adapter files..
OPTION="--adapter-sequence <adapter dirrectory>/adapter.fa"

#Nextera or dual index single index (8bp)
BM_OPTION="--use-bases-mask Y*,I8,Y*"   # what is with the aligned1 output dir? Convention??
#Truseq 6bp index on a dual index run (6 bp)
BM_OPTION="--use-bases-mask Y*,I6nn,Innnnnnnn,Y*"
#Truseq 6bp index on a single index dual run (6 bp)
BM_OPTION="-use-bases-mask Y*,I6nn,Y*"
#Dual index sample on a dual index run (8bp, 8bp)
BM_OPTION="--use-bases-mask Y*,I8,I8,Y*"
# Amplicon SR Index Fastq generation
BM_OPTION="--use-bases-mask y151,y12"
#Amplicon Miseq Run full demutiplex
BM_OPTION="-use-bases-mask y*,I12,y*"
#Amplicon PE Index Fastq generation
BM_OPTION="--use-bases-mask y151,y12,y151"

##### ??? <TALK TO SARAH ABOUT THIS>
#  Misc quailfer examples off of the standard. Note these quailifers can be added to any of the roots above and more than one may need to be used at a time. 




# execute the actual commands
cd ${INPUT}
configureBclToFastq.pl --input-dir ${INPUT} --output-dir ${OUTPUT}  ${OPTION} --fastq-cluster-count 0 --sample-sheet ${SAMPLESHEET} 
make -j ${THREADS}
bcl2fastq2
