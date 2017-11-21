#!/bin/bash


# # this script pushes a run folder to shock, creating 3 different subsets
#
# a) entire run folder (minus fastq files and minus thumbnails); a single tar.gz file ${RUN_FOLDER_NAME}.tar.gz
# b) multiple fastq files and SAV.tar.fz file are stored (the SAV file includes the Samplesheets and other documents required for the Illumina SAV tool)
# c) thumbnail files (a single tar.gz file): example: ${RUN_FOLDER_NAME}.tumbnails.tar.tgz
# all 3 files are required to obtain the entire RUN_Folder (note the SAV files are stored twice)


# constants
SHOCK_SERVER="http://shock.metagenomics.anl.gov"
TMP_FILE="/var/tmp/$$.shock_read_tmp_file.$$"

# ##############################
# ##############################
# include a library of basic functions for SHOCK interaction
INSTALL_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )

if [ -z ${SOURCES+x} ]; then

        SOURCE_CONFIG=${BIN}/../SHOCK_functions.sh

        if [ ! -e ${SOURCE_CONFIG} ]; then
                echo "source config file ${SOURCE_CONFIG} not found"
                exit 1
        fi

        source ${SOURCE_CONFIG} # this defines ${SOURCES}

fi
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

function secure_shock_read {
	local REMOTE_MD5=$1
	local NODE_ID=$2
  local TARGET_PATH=$3

	# need to check for presence of parameters
	# if there is no  JSON or FILENAME or the file is not readable
  if  [[ "${NODE_ID}_x" == "_x" ]]
		then
			echo "$0 function secure_shock_read:: missing NODE_ID"
			exit 1
	fi

	if [[ "${REMOTE_MD5}_x" == "_x" ]]   # we might want to test if we can create the file .. -o  [ -w "${FILENAME}" ] ]
	then
		echo "$0 function secure_shock_read:: missing MD5 checksum"
		exit 1
	fi

# now download the file
	res=$(curl --silent -X GET -H "${AUTH}" "${SHOCK_SERVER}/node/${NODE_ID}/?download" > ${TARGET_PATH})

	# compute MD5 checksum for the input file
	# note this will need to be changed when not running on a Mac
	FILE_MD5=$(md5sum -b ${TARGET_PATH} | cut -f1 -d\  ) # for Linux

  # return _SHICK_ERROR if MD5 sums don't match
  if [[ ${FILE_MD5} != ${REMOTE_MD5} ]]
  then
    echo "SHOCK_ERROR"
    exit 1
  	# for now
#    echo "$0 MD5 checksum mismatch for ${FILENAME}, aborting (local-md5:(${FILE_MD5}), remote-md5:(${REMOTE_MD5})"
  else
	  # return the remote MD5 fingerprint
	  echo ${FILE_MD5}
  fi
}




# make sure all files are deleted if we exit prematurely or die
function clean_up {

	# Perform program exit housekeeping
	rm -f ${TMP_TAR_FILE}
	exit
}
trap clean_up SIGHUP SIGINT SIGTERM

rm -f ${TMP_TAR_FILE}

function usage {
echo "Usage: $0 [-h <help>] [a|t|r|f] -r <run folder> "
}

# get options
while getopts hr: option; do
    case "${option}"
        in
		h) HELP=1;;
		r) RUN_FOLDER=${OPTARG};;
		*)
		usage
		;;
    esac
done

# make sure we have at least a run folder name
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
# use the JQ tool to parse the correct IDs for the SHOCK objects from the return JSON struct
#    the correct invocation is --> jq -r '{ data: .data[].id  } '  <--


echo "obtaining list of files for  ${RUN_FOLDER} .. \c"

FASTQ_FILES_JSON=$(
curl --silent -X GET -H "${AUTH}" "${SHOCK_SERVER}/node?query&type=run-folder-archive-fastq&project_id=${RUN_FOLDER}"  )
echo " done"

# create a flat list
FASTQ_FILES_IDS=$(echo "${FASTQ_FILES_JSON}" | jq  -r ' { node: .data[].id } ' | IFS='}' cut -d: -f2 | tr -d '}{\n"' )

echo "Found $(echo ${FASTQ_FILES_IDS} | wc -w) Files"

# walk thru all the FASTQ files, tar file later
for  NODE_ID in ${FASTQ_FILES_IDS}
do
  #set -xv
  # obtain info about the node
  NODE_JSON=$(curl --silent -X GET -H "${AUTH}" "${SHOCK_SERVER}/node/${NODE_ID}" )

#  echo "${NODE_JSON}" | jq '.'

	## parse additional project specific fields
	filename=$(echo $NODE_JSON | jq '  .data.file.name  ' | tr -d '""')
  SHOCK_MD5=$(echo ${NODE_JSON} | jq ' .data.file.checksum.md5 ' | tr -d '""')
  group=$(echo ${NODE_JSON} | jq ' .data.attributes.group  '| tr -d '""')
  project=$(echo ${NODE_JSON} | jq ' .data.attributes.project  '| tr -d '""') # prepend Project_
  sample=$(echo ${NODE_JSON} | jq ' .data.attributes.sample  '| tr -d '""')  # prepend Sample_

  echo "group: ${group} sample: ${sample} project: ${project}"

  exit

# read file and compare MD5s
echo "$0 downloading ${filename} with MD5 ${SHOCK_MD5} .. \c"

   RET_VAL=$(secure_shock_read ${SHOCK_MD5} ${NODE_ID} ${TMP_FILE})

   if [[ ${RET_VAL} == "SHOCK_ERROR" ]]
   then
     echo "failed"
     echo "$0 cannot read SHOCK node ${NODE_ID} for file: ${filename}"
   else
     echo "done"
  	# where does the file need to go
  	declare TARGET_PATH=${project}/${sample}/${filename}

  	# make sure the target path exists
  	mkdir -p ${sample}/${project}/${sample}
    mv ${TMP_FILE} ${TARGET_PATH}
 fi
done

set -xv
# now handle the sav.tar.gz file
TAR_FILE_JSON=$(
curl --silent -X GET -H "${AUTH}" "${SHOCK_SERVER}/node?query&type=run-folder-archive-sav&project_id=${RUN_FOLDER}"  )

# create a flat list
NODE_ID=$(echo "${TAR_FILE_JSON}" | jq  -r ' { node: .data[].id } ' | IFS='}' cut -d: -f2 | tr -d '}{\n" ' )

  # obtain info about the node
  NODE_JSON=$(curl --silent -X GET -H "${AUTH}" "${SHOCK_SERVER}/node/${NODE_ID}" )

#  echo "${NODE_JSON}" | jq '.'

	## parse additional project specific fields
	filename=$(echo $NODE_JSON | jq '  .data.file.name  ' | tr -d '""')
  SHOCK_MD5=$(echo ${NODE_JSON} | jq ' .data.file.checksum.md5 ' | tr -d '""')

  RET_VAL=$(secure_shock_read ${NODE_ID} ${SHOCK_MD5}  ${TMP_FILE})

if [[ ${RET_VAL} == "SHOCK_ERROR" ]]
  then
    echo "failed"
    echo "$0 cannot read SHOCK node ${NODE_ID} for file: ${filename}"
  else
    echo "done"

 # extract SAV files
  return=`tar xfz ${TMP_FILE}  `
  if [[ $return != "" ]]
  then
  echo "$0 tar command failed [ $? ] "
  rm -f ${TMP_FILE}
  fi
fi

# cleanup
