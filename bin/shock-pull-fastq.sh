#!/bin/bash


# # this script pushes a run folder to shock, creating 3 different subsets
# 
# a) entire run folder (minus fastq files and minus thumbnails); a single tar.gz file ${RUN-FOLDER-NAME}.tar.gz
# b) multiple fastq files and SAV.tar.fz file are stored (the SAV file includes the Samplesheets and other documents required for the Illumina SAV tool)
# c) thumbnail files (a single tar.gz file): example: ${RUN-FOLDER-NAME}.tumbnails.tar.tgz
# all 3 files are required to obtain the entire RUN-Folder (note the SAV files are stored twice)


# constants
SHOCK_SERVER="http://shock.metagenomics.anl.gov"
TMP_FILE="/var/tmp/$$.shock_read_tmp_file.$$"


# ##############################################
# ##############################################
# ##############################################
function secure_shock_read {
	local JSON=$1
	local FILENAME=$2
 	
	# need to check for presence of parameters 
	# if there is no  JSON or FILENAME or the file is not readable
  if [  [ "${JSON}_x" == "_x" ]  ]
		then
			echo "$0 function secure_shock_read:: missing JSON parameters"
			exit 1		
	fi
	
	if [ [ "${FILENAME}_x" == "_x" ]  ]   # we might want to test if we can create the file .. -o  [ -w "${FILENAME}" ] ]
	then
		echo "$0 function secure_shock_read:: missing filename"
		exit 1
	fi
	
# now download the file
	res=`curl -H ${AUTH} GET ${SHOCK-SERVER}/node${file}/?download > ${TARGET_PATH}`

# check if we get an error code
	if [[ $res != 0 ]]
		then
			echo "download failed ($filename)"
			exit 1
	fi

# get the MD5 to ensure we got the correct file
	JSON=`curl -H ${AUTH} GET ${SHOCK-SERVER}/node/${file} `
	# if there is no return JSON and or we see an error status we report and die
  if [  "${JSON}" == ""  ] 
		then
			echo "can't get feedback for upload (${FILENAME}, ${ERROR_STATUS})"
			exit 1		
	fi
	
	# grab error status from JSON return	
	SHOCK_MD5=`echo ${JSON} | jq -r '{ md5: .data[].file.checksum.md5` } '		
			
	# if there is no return JSON and or we see an error status we report and die
  if [  ${SHOCK_MD5} == "" ]
		then
			echo "can't get an MD5 from SHOCK for (${$i})"
			exit 1		
	fi
	
	# return the remote MD5 fingerprint
	echo ${SHOCK_MD5}
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
echo "restore Illumina runs from SHOCK archive"
echo "Usage: $0 [-h <help>] [a|t|r|f] -r <run folder> "
echo "-t -- just thumbails"
echo "-x -- just raw"
echo "-f -- just FASTQ files and SAV files"
echo "-a -- all files"
 }

# get options
while getopts afthr: option; do
    case "${option}"
        in
		h) HELP=1;;
		r) RUN_FOLDER=${OPTARG};;
	a)	TASK=a;;
	f)	TASK=f;;
	x)	TASK=r;;
	t)	TASK=t;;
		*)
		usage
		;;
    esac
done

# make sure we have at least a run folder name
if [ -z ${RUN_FOLDER} -o -z ${TASK} ]
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

echo -ne "obtaining list of files for  ${RUN_FOLDER .. "


FASTQ_FILES_JSON=`
curl -X GET -H "S{AUTH}" "${SHOCK_SERVER}/node/node/order=created_on&direction=desc&offsEt=0&querynode&attributes.data_type=run-folder-archive-fastq&project_id=${RUN_FOLDER}"  `

# sample jq output
# {
#  "data": "5c44f98b-a83f-4320-ac30-abdcad64c7fa",
#  "name": "error",
#  "md5": "b0343349b7f7b3ab6550c649a3299a9d",
#  "length": 376,
#  "owner": "anonymous"
# }

echo " done"

#FASTQ_FILES_IDS=echo "${FASTQ_FILES_JSON}" | jq -r '{ data: .data[].id  } ' | tr -d " {}\"" | fgrep data | cut -f2 -d:
#USE JQ to parse JSON install via "wget -O jq https://github.com/stedolan/jq/releases/download/jq-1.5/jq-linux64"

# parse filename, project, group, sample , md5 and length from JSON struct
PARSED_JSON= `echo ${FASTQ_FILES_JSON} | jq -r '{ data: .data[] .id , name: .data[].file.name , md5: .data[].file.checksum.md5 , length: .data[].file.size, project: .data[].attributes.project , group: .data[].attributes.group , sample: .data[].attributes.sample}  ' |  awk '  BEGIN { RS="\}" } { print  $3 $5 $7 $9 } ' ` | tr -d "\" `

for i in ${PARSED_JSON}
do
	
	# this could be done cleaner and more robust with jq
	NODE_ID=$(echo $i | awk -F/  '{print $1 }'  )
	
	FILE_NAME=$(secure_shock_read $JSON $NODE_ID)
	
	# if we find a tar file go ahead and unpack it
	if ( echo ${FILE_NAME} | fgrep tar.gz )
	then
		tar xf ${FILE_NAME}
		rm -f ${FILE_NAME}
	fi
	
	# parse additional project specific fields
	filename=`echo $i | awk -F/  '{print $2 }'  `
	SHOCK_MD5=`echo $i | awk -F/  '{print $3 }'  `
	group=`echo $i | awk -F/  '{print $2 }' `
	sample="Sample_"`echo $i | awk -F/  '{print $4 }' | sed s/Sample_//g`
	project="Project_"`echo $i | awk -F/  '{print $3 }' | sed s/Project_//g`


REMOTE_MD5=$(secure_shock_read ${JSON} ${TMP_FILE})

# check md5
# compute MD5 checksum for the input file
# note this will need to be changed when not running on a Mac	
FILE_MD5=`md5 -q ${TMP_FILE}`		
#FILE_MD5=`md5sum $i` # for Linux
if [[ ${FILE_MD5} != ${SHOCK_MD5} ]]
		then
			echo "$0 MD5 checksum mismatch for ${FILENAME}, aborting (local-md5:(${FILE_MD5}), remote-md5:(${SHOCK_MD5})"
			exit 1	
fi


	# where does the file need to go
	TARGET_PATH=${project}/${project}/${sample}/${filename}
	
	# make sure the target path exists 
	mkdir -p ${sample}/${project}/${sample}

# now download the file
	echo -ne "downloading ${filename} .. "
	res=`curl -H ${AUTH} GET ${SHOCK-SERVER}/node${file}/?download > ${TARGET_PATH}`

# check if we get an error code
	if [[ $res != 0 ]]
		then
			echo "download failed ($filename)"
			exit 1
	fi

# get the MD5 to ensure we got the correct file
	JSON=`curl -H ${AUTH} GET ${SHOCK-SERVER}/node/${file} `
	# if there is no return JSON and or we see an error status we report and die
  if [  "${JSON}" == ""  ] 
		then
			echo "can't get feedback for upload (${FILENAME}, ${ERROR_STATUS})"
			exit 1		
	fi
	
	# grab error status from JSON return	
	SHOCK_MD5=`echo ${JSON} | jq -r '{ md5: .data[].file.checksum.md5` } '		
			
	# if there is no return JSON and or we see an error status we report and die
  if [  ${SHOCK_MD5} == "" ]
		then
			echo "can't get an MD5 from SHOCK for (${$i})"
			exit 1		
	fi
	
	echo "done"

done




# find SAV files now and tar them
TMP_TAR_FILE= ""    # get from SHOCK

# extract SAV files
return=`tar xfz ${TMP_TAR_FILE}  `
if [[ $return != "" ]]
then
echo "$0 tar command failed [ $? ] "
rm -f ${TMP_TAR_FILE}
fi

# cleanup 







