#!/bin/bash

# remove all available files for a given RUN_FOLDER_NAME

# constants
SHOCK_SERVER="http://shock.metagenomics.anl.gov"

rm -f ${TMP_TAR_FILE}

function usage { 
echo "list files available for RUN_FOLDER_NAME "
echo "Usage: $0 [-h <help>] -r <run folder> -x"
 }

# get options
while getopts hrx: option; do
    case "${option}"
        in
		h) HELP=1;;
		r) RUN_FOLDER=${OPTARG};;
		x) DELETE=1;;
		*)
		usage
		;;
    esac
done

if [ ${DELETE} ]
	then
		echo "removing FASTQ + SAV files in 5 seconds [time for CTRL-C now...]"
		sleep 5
		rm -rf ${SAV_FILES} ${FASTQ_FILES}
	fi

# make sure the name has no path
RUN_FOLDER_NAME=$(basename ${RUN_FOLDER})
#init our file counter
counter=0

# exit on any error
set -e 

if [ ! -e ${RUN_FOLDER} ]
then
	echo "$0 RUN_FOLDER not defined"
	exit 1
fi
FILES_JSON=`
curl --silent -X GET -H "S{AUTH}" "${SHOCK_SERVER}/node?query&project_id=${RUN_FOLDER}"  `


BELTS_AND_SUSPENDERS=$(echo "${FILES_JSON}" | jq -r  '{ error: .error }' |  IFS='}' cut -d: -f2 | tr -d "}{\n\"\ "  )


exit

# check for error
ERROR_STATUS=$(echo "${FILES_JSON}" | jq -r  '{ error: .error }' |  IFS='}' cut -d: -f2 | tr -d "}{\n\"\ "  )

# die if we catch an error
if [ "${ERROR_STATUS}" != "null"  ]
	then
		echo "$0 :: error obtaining list of objects for ${RUN_FOLDER} (${ERROR_STATUS})"
		exit 1		
fi

NODES=$(echo ${FILES_JSON} | jq ' .data[].id ' | tr -d \")

# list each object in JSON 
for i in ${NODES}
do
	
	echo "NODE::${i}"

#	RVAL=$(curl -X DELETE --silent -H "${AUTH}" "${SHOCK_SERVER}/node/${i}" )
	RVAL=$(curl --silent -H "${AUTH}" "${SHOCK_SERVER}/node/${i}" )

	ERROR_STATUS=$(echo "${RVAL}" | jq -r  '{ error: .error }' |  IFS='}' cut -d: -f2 | tr -d "}{\n\"\ "  )

		# die if we catch an error
		if [ "${ERROR_STATUS}" != "null"  ]
			then
				echo "$0 :: error obtaining list of objects for ${RUN_FOLDER} (${ERROR_STATUS})"
				exit 1		
		fi
		
	counter=`expr $counter + 1 `

done

echo "deleted ${counter} objects for RUN-FOLDER ${RUN_FOLDER_NAME}"



