#!/bin/bash
# find_coding_schemes.sh FOR ANL Sequencing core

#defaults
THREADS=8

# set option
HELP=0
INPUT=''
OUTPUT=''


usage () { 
	echo "Usage: find_coding_schemes.sh [-h <help>] -r <run folder> "
 }

# get options
while getopts hr: option; do
    case "${option}"
        in
            h) 	HELP=1;;
            r) 	RUN_FOLDER=${OPTARG};;
		*)
			usage
			;;
    esac
done


if [[ -z ${RUN_FOLDER} ]]
then
	usage
	exit 1
fi

# 
if [  ! -d ${RUN_FOLDER} ] 
then
	echo "$0 ${RUN_FOLDER} not found"
	usage
	exit 1
fi

# check for presence of RTAComplete.txt
if [ ! -e ${RUN_FOLDER}/RTAComplete.txt ] 
then
	echo "$0 ${RUN_FOLDER} is incomplete, RTAComplete.txt is not present. Aborting"
	exit 1
fi	

# go to the place
cd ${RUN_FOLDER}

SAMPLE_SHEETS=`ls SampleSheet*.csv`

# each barcoding scheme is represented by one Sample sheet (default is just one; up to 3 have been used in a single run)

for i in ${SAMPLE_SHEETS}
do
	echo "Found SampleSheet $i"
    echo "this is where bcl2fast2 run params are written to a parameter file, the --use-bases-mask parameter needs to be added manually"	
done

