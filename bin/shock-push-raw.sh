#!/bin/bash


# # this script pushes a run folder to shock, creating 3 different subsets
# 
# a) entire run folder (minus fastq files and minus thumbnails); a single tar.gz file ${RUN_FOLDER_NAME}.tar.gz
# b) multiple fastq files and SAV.tar.fz file are stored (the SAV file includes the Samplesheets and other documents required for the Illumina SAV tool)
# c) thumbnail files (a single tar.gz file): example: ${RUN_FOLDER_NAME}.tumbnails.tar.tgz
# all 3 files are required to obtain the entire RUN_Folder (note the SAV files are stored twice)


# #############################################
# constants

SHOCK_SERVER="http://shock.metagenomics.anl.gov"
TMP_TAR_FILE="/var/tmp/temporary-tar-file-shock-client.$$.tar.gz"
FILE_NAME_LIST_FILE=/var/tmp/$$._tar_name_list.txt.$$

rm -f ${TMP_TAR_FILE}
# #############################################
# make sure all files are deleted if we exit prematurely or die
function clean_up {

	# Perform program exit housekeeping
	rm -f ${TMP_TAR_FILE} ${FILE_NAME_LIST_FILE}
	exit
}
trap clean_up SIGHUP SIGINT SIGTERM

# #############################################
# #############################################
# #############################################

# ##############################
# ##############################
# include a library of basic functions for SHOCK interaction
INSTALL_DIR=`dirname $0`
source ${INSTALL_DIR}/SHOCK_functions.sh

	# #############################################
	# #############################################
	# #############################################

function usage  { 
	echo "Usage: shock-push-raw.sh [-h <help>] [-d] -r <run folder> "
    echo " -d  delete files after upload"
 }
 
 # get options
 while getopts hdr: option; 
 	do
  		 case "${option}"	in
 		h) HELP=1;;
 		r) RUN_FOLDER=${OPTARG};;
 		d) DELETE=1;;
 		*)
 		usage
 		;;
     esac
 done
# 
if [ -z ${RUN_FOLDER} ]
then
	usage
	exit 1
fi

if [ ! -d ${RUN_FOLDER} ]
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

# strip the prefix of the run folder to get the name 
RUN_FOLDER_NAME=`basename ${RUN_FOLDER}`

# terminate on error
set -e

# fastq files
cd ${RUN_FOLDER}

echo  "Obtaining list of files .."
# build a list of files excluding Thumbnails, FASTQs and SAV files
FILES=`find ./ -type f | fgrep -v fastq  | fgrep -v Thumbnail_Image  `
# old version that excludes SAV files as well
#FILES=`find ./ -type f | fgrep -v fastq  | fgrep -v Thumbnail_Image | fgrep -v InterOp | fgrep -v RunInfo.xml | fgrep -v runParameters.xml | fgrep -v Samplesheet.csv `
echo "done"

# create a tmp file with the filenames
echo "${FILES}" > ${FILE_NAME_LIST_FILE}

echo  "creating tar file .."
# tar up the files using a file of filenames
res=`tar cfz ${TMP_TAR_FILE} -T ${FILE_NAME_LIST_FILE} > /dev/null`
# check on the return value
if [ ! $? -eq 0 ]
then 
  echo "$0 Could not create raw tar file " >&2
	# remove the tmp file
	rm -f ${FILE_NAME_LIST_FILE}
  exit 1	
fi
echo "done"

# remove the tmp file
rm -f ${FILE_NAME_LIST_FILE}

# echo message about not setting expiry date
echo "Folker: remember to set automatic expiry data "

JSON="{ \"type\" : \"run-folder-archive-raw\", \
\"name\" : \"${RUN_FOLDER_NAME}.raw.tar.gz\", \
\"project_id\" : \"${RUN_FOLDER_NAME}\" ,\
\"owner\" : \"${OWNER}\" \
}"

# obtain a node ID ( "-1" if file already exits in SHOCK)
NODE_ID=$(secure_shock_write "${JSON}" "${TMP_TAR_FILE}" "${RUN_FOLDER_NAME}-run-folder-archive-raw.tar.gz") 

# if the file does not already exist, we set an expiration date
if [ "${NODE_ID}" == "-1" ]
then
# set expiration date for RAW files
echo "setting 60 day expiration date"
#curl -X PUT -H "${AUTH}" -F "expiration=90D" "${SHOCK_SERVER}/${NODE_ID}"
fi

if [ -n "${DELETE}"  ]
then
	echo "removing all files except FASTQ, SAV and Thumbnails in 5 seconds [time for CTRL-C now...]"
	sleep 5
	rm -rf ${FILES}
fi

# clean up existing temp files 
clean_up





