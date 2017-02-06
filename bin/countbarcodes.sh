#!/bin/bash

usage () {
	echo "Usage: countbarcodes.sh <input_file>"
	echo "[-s] sample (use only 250,000 lines instead of entire file)"
}

while getopts hs: option; do
    case "${option}"
        in
	s) 	SAMPLE=1;;
	h)	usage ; exit ;;
	*) usage  ; exit 1 ;;
    esac
done

if [[ ${1} == "" ]]
then
	usage
	exit 1
fi


if [[ $0 =~ countbarcodessample.sh ]] 
then
LINES=1000000     # 250 Thousand reads
#      .  .
else
LINES=1000000000  # 250 Million Reads.
fi
#      .  .  .
target=$1

if [[ -e $target ]] 
then
HEADER=$( zcat $target  | head -n 1 | cut -c 1-5 )
# echo Header line:  $( zcat $target | head -n 1 ) 
# Create file containing barcodes, one per line
zcat $1 | head -n $LINES | grep ^$HEADER | tr ':' ' ' | cut -d ' ' -f 11 | sort | uniq -c  | awk '{print $2 "\t" $1 }' | sort -k 2 -n   
else
echo Can\'t find file $target !
fi

