#!/bin/bash

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

