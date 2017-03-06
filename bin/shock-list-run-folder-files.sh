#!/bin/bash

# list all available files for a given RUN_FOLDER_NAME

# constants
SHOCK_SERVER="http://shock.metagenomics.anl.gov"
TMP_TAR_FILE="/var/tmp/temporary-tar-file-shock-client.$$.tar.gz"

# make sure all files are deleted if we exit prematurely or die
function clean_up {

	# Perform program exit housekeeping
	rm -f ${TMP_TAR_FILE}
	exit
}
trap clean_up SIGHUP SIGINT SIGTERM

rm -f ${TMP_TAR_FILE}

function usage { 
echo "list files available for RUN_FOLDER_NAME "
echo "Usage: $0 [-h <help>] -r <run folder> "
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
if [ -z ${RUN_FOLDER} ]
then
usage
exit 1
fi

# make sure the name has no path
RUN_FOLDER_NAME=`basename ${RUN_FOLDER}`
#init our file counter
counter=0

# exit on any error
set -e 

FILES_JSON=$(curl --silent -X GET -H "${AUTH}" "${SHOCK_SERVER}/node?query&project_id=${RUN_FOLDER}" )

# check for error
ERROR_STATUS=$(echo "${FILES_JSON}" | jq -r  '{ error: .error }' |  IFS='}' cut -d: -f2  | tr -d "}{\n\"\ "  )

# die if we catch an error
if [ "${ERROR_STATUS}" != "null"  ]
	then
		echo "$0 :: error obtaining list of objects for ${RUN_FOLDER} (${ERROR_STATUS})"
		exit 1		
fi

echo ${FILES_JSON} | jq ' .data[].file.name ' 