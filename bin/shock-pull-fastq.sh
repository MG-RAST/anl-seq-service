#!/bin/bash


# # this script pushes a run folder to shock, creating 3 different subsets
# 
# a) entire run folder (minus fastq files and minus thumbnails); a single tar.gz file ${RUN-FOLDER-NAME}.tar.gz
# b) multiple fastq files and SAV.tar.fz file are stored (the SAV file includes the Samplesheets and other documents required for the Illumina SAV tool)
# c) thumbnail files (a single tar.gz file): example: ${RUN-FOLDER-NAME}.tumbnails.tar.tgz
# all 3 files are required to obtain the entire RUN-Folder (note the SAV files are stored twice)


# constants
SHOCK_SERVER="http://shock.metagenomics.anl.gov"
TMP_TAR_FILE="/var/tmp/temporary-tar-file-shock-client.$$.tar.gz"
AUTH=""

rm -f ${TMP_TAR_FILE}

name=`basename $0`
usage () { 
	echo "Usage: ${name} [-h <help>] -r <run folder> "
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


# exit on any error
set -e 

# create folder if not already present
mkdir -p ${RUN_FOLDER}

# fastq files
cd ${RUN_FOLDER}

# query shock for FASTQ and SAV files 
FASTQ_FILES="" #ADD HERE

for i in ${FASTQ_FILES}
do
	# use Illumina directory structure to extract group (e.g. unaligned), project and sample info.
	# ./unaligned/Project_AR3/Sample_AR314/AR314_GGAACT_L003_R1_001.fastq.gz  [sample $i]
	
	echo "QUESTION: Do we want to restore the original directory structure?"
	
	group=`echo $i | awk -F/  '{print $2 }' `
	project=`echo $i | awk -F/  '{print $3 }' | sed s/Project_//g`
	sample=`echo $i | awk -F/  '{print $4 }' | sed s/Sample_//g`
	file=`echo $i | awk -F/  '{print $5 }' `

	JSON="	{ \"run-folder\" : \"${RUN_FOLDER_NAME}\" , \
				  \"type\" : \"run-folder-archive-fastq\" , \
   			 	\"group\" : \"$group\", \
				\"project\" : \"$project\",\		
				\"sample\" : \"$sample\",\
				\"name\" : \"$file\",\	
				\"organization\" : \"ANL-SEQ-Core\" }" 
								
		# with file, without using multipart form (not recommended for use with curl!)
#		curl -X POST ${AUTH} -F "attributes_str=${JSON}" --data-binary $i  ${SHOCK-SERVER}/node
	echo ${JSON}
done

# find SAV files now and tar them
TMP_TAR_FILE= ""    # get from SHOCK

# extract SAV files
return=`tar xfz ${TMP_TAR_FILE}  `
if [[ $return != 0 ]]
then
	echo "$0 tar command failed [ $? ] "
	rm -f ${TMP_TAR_FILE}
fi

# cleanup 







