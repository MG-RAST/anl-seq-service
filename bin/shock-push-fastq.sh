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


usage () { 
	echo "Usage: shock-push.sh [-h <help>] [-d] -r <run folder> "
    echo " -d  delete files after upload"
 }

# get options
while getopts hr: option; do
    case "${option}"
        in
		h) HELP=1;;
		r) RUN_FOLDER=${OPTARG};;
		d) DELETE=1;;
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

# exit on any error
set -e 

# strip the prefix of the run folder to get the name 
RUN_FOLDER_NAME=`basename ${RUN_FOLDER}`

# fastq files
cd ${RUN_FOLDER}
FASTQ_FILES=`find ./ -name \*.fastq\*`
for i in ${FASTQ_FILES}
do
	# use Illumina directory structure to extract group (e.g. unaligned), project and sample info.
	# ./unaligned/Project_AR3/Sample_AR314/AR314_GGAACT_L003_R1_001.fastq.gz  [sample $i]
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

# from documentation SAV files are:  RunInfo.xml, runParameters.xml, SampleSheet.csv, InterOp  (directory)
SAV_FILES="RunInfo.xml runParameters.xml SampleSheet.csv InterOp/*"

return=`tar cfz ${TMP_TAR_FILE} ${SAV_FILES} `
if [[ $return != "" ]]
then
	echo "$0 tar command failed [ $? ] "
	rm -f ${TMP_TAR_FILE}
fi

JSON="	{ \"run-folder\" : \"${RUN_FOLDER_NAME}\" , \
		  \"type\" : \"run-folder-archive-sav\" , \
		\"name\" : \"${RUN_FOLDER_NAME}-sav.tar.gz\" ,\
		\"organization\" : \"ANL-SEQ-Core\" }" 
						
# with file, without using multipart form (not recommended for use with curl!)
#curl -X POST ${AUTH} -F "attributes_str=${JSON}" --data-binary ${TMP_TAR_FILE}  ${SHOCK_SERVER}/node

if [[ ${DELETE_FILES} == "1" ]]
	then
		cd ${RUN_FOLDER}
		echo "removing FASTQ + SAV files in 5 seconds [time for CTRL-C now...]"
		sleep 5
		# rm -rf ${SAV_FILES} ${FASTQ_FILES}
	fi

# cleanup
exit 1
rm -f ${TMP_TAR_FILE}
 







