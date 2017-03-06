#!/bin/bash


# # this script pushes a run folder to shock, creating 3 different subsets
# 
# a) entire run folder (minus fastq files and minus thumbnails); a single tar.gz file ${RUN_FOLDER_NAME}.tar.gz
# b) multiple fastq files and SAV.tar.fz file are stored (the SAV file includes the Samplesheets and other documents required for the Illumina SAV tool)
# c) thumbnail files (a single tar.gz file): example: ${RUN_FOLDER_NAME}.tumbnails.tar.tgz
# all 3 files are required to obtain the entire RUN-Folder (note the SAV files are stored twice)


# constants
SHOCK_SERVER=http://shock.metagenomics.anl.gov
TMP_TAR_FILE=/var/tmp/temporary-tar-file-shock-client.$$.tar.gz
AUTH=

rm -f ${TMP_TAR_FILE}


usage () { 
	echo "Usage: shock-push.sh [-h <help>] -r <run folder> "

 }

# get options
while getopts hr: option; do
    case "${option}"
        in
		h) HELP=1;;
		r) RUN_FOLDER=${OPTARG};;
#		d) DELETE_FOLDER=1;; leave for later
		*)
		usage
		;;
    esac
done

# 
if [[ ! -d ${RUN_FOLDER} ]]
then
	echo "$0 ${RUN_FOLDER} not found"
	usage
	exit 1
fi

# check for presence of RTAComplete.txt
if [[ ! -e ${RUN_FOLDER}/RTAComplete.txt ]]
then
	echo "$0 ${RUN_FOLDER} is incomplete, RTAComplete.txt is not present. Aborting"
	exit 1
fi	 

# strip the prefix of the run folder to get the name 
RUN_FOLDER_NAME=`basename ${RUN_FOLDER}`

# fastq files
cd ${RUN_FOLDER}
FASTQ_FILES=`find ./ -name \*.fastq\*`
for i in ${FASTQ_FILES}
do
	echo $i

	# use Illumina directory structure to extract group (e.g. unaligned), project and sample info.
	echo $i | awk -F/  '{print $2 $3 $4 $5}' | while read  group project sample file
	do
	    echo $group $project $sample $file

		# with file, without using multipart form (not recommended for use with curl!)
		curl -X POST     -F 'attributes_str={ "RUN-FOLDER" : '${RUN_FOLDER_NAME} '}' \
						 -F 'attributes_str={ "type" : "run-folder-archive"}' \
						 -F 'attribute_str={ "group" : "$group" }' \
						 -F 'attribute_str={ "project" : "$project" }' \		
						 -F 'attribute_str={ "sample" : "$sample" }' \
						 -F 'attribute_str={ "name" : "$file" }' \	
						 -F 'attribute_str={ "Organization" : "ANL-SEQ-Core" }' \
							 --data-binary $i ${AUTH} ${SHOCK_SERVER}/node
	done
done




exit 1

# 
echo "pruning goes here, to be added later after discussing with SARAH"


echo "tar and gzip goes here"
return=`tar cfz ${TMP_TAR_FILE} ${RUN_FOLDER} `
if [[ $return != "" ]]
then
	echo "$0 tar command failed [ $? ] "
	rm -f ${TMP_TAR_FILE}
fi





