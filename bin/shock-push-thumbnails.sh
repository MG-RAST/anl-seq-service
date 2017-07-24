#!/bin/bash


# # this script pushes a run folder to shock, creating 3 different subsets
# 
# a) entire run folder (minus fastq files and minus thumbnails); a single tar.gz file ${RUN_FOLDER_NAME}.tar.gz
# b) multiple fastq files and SAV.tar.fz file are stored (the SAV file includes the Samplesheets and other documents required for the Illumina SAV tool)
# c) thumbnail files (a single tar.gz file): example: ${RUN_FOLDER_NAME}.tumbnails.tar.tgz
# all 3 files are required to obtain the entire RUN_Folder (note the SAV files are stored twice)


# #############################################
# constants
SHOCK_SERVER=http://shock.metagenomics.anl.gov
TMP_TAR_FILE=/var/tmp/temporary-tar-file-shock-client.$$.tar.gz
FILE_NAME_LIST_FILE=/var/tmp/$$._tar_name_list.txt.$$

# #############################################
# make sure all files are deleted if we exit prematurely or die
function clean_up {

	# Perform program exit housekeeping
	rm -f ${TMP_TAR_FILE} ${FILE_NAME_LIST_FILE}
	exit
}
trap clean_up SIGHUP SIGINT SIGTERM

# ##############################
# ##############################
# include a library of basic functions for SHOCK interaction
INSTALL_DIR=`dirname $0`
source ${INSTALL_DIR}/SHOCK_functions.sh

# ##############################
# ##############################
# we could create a file with project wide defaults to set for all scripts
if [ -e "${INSTALL_DIR}/PROJECT_settings.sh" ]
then
	source ${INSTALL_DIR}/PROJECT_settings.sh
fi

#
# source auth.env file with credentials
# from either HOME DIR (priority) or install dir
set -o allexport
if [[ -e ${HOME}/.shock-auth.env ]]
then
  source ${INSTALL_DIR}/auth.env    
elif [[ -e ${INSTALL_DIR}/auth.env ]]
then
  source ${INSTALL_DIR}/auth.env  
fi
set +o allexport


# ##############################
# ##############################
# ##############################
# ##############################


rm -f ${TMP_TAR_FILE}


function usage { 
	echo "Usage: shock-push-thumbnails.sh [-h <help>] [-d] -r <run folder> "
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

res=`tar cfz ${TMP_TAR_FILE} Thumbnail_Images/`

if [ ! $? -eq 0 ]
then 
  echo "$0 Could not create Thumbnail tar file " >&2
  exit 1
fi

# with file, without using multipart form (not recommended for use with curl!)
JSON="{ \"type\" : \"run-folder-archive-thumbnails\",\
\"project_id\" : \"${RUN_FOLDER_NAME}\" ,\
\"name\" : \"${RUN_FOLDER_NAME}.thumbnails.tar.gz\",\
\"owner\" : \"${OWNER}\" \
}"

# obtain a node ID ( "-1" if file already exits in SHOCK)
NODE_ID=$(secure_shock_write "${JSON}" "${TMP_TAR_FILE}" "${RUN_FOLDER_NAME}-thumbnails.tar.gz")

# check if the 
if [ "${NODE_ID}" == "-1" ]
then
# set expiration date for RAW files
echo "setting 60 day expiration date"
curl -X PUT -h "${AUTH}" -F "expiration=60D" "${SHOCK_SERVER}/${NODE_ID}"
fi

# clean up
rm -f ${TMP_TAR_FILE}

if [ -n "${DELETE}"  ]
then
	echo "removing Thumbnails in 5 seconds [time for CTRL-C now...]"
	sleep 5
	rm -rf ${RUN_FOLDER}/Thumbnail_images
fi




