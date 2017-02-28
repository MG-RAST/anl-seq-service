#!/bin/bash


# # this script pushes a run folder to shock, creating 3 different subsets
# 
# a) entire run folder (minus fastq files and minus thumbnails); a single tar.gz file ${RUN-FOLDER-NAME}.tar.gz
# b) multiple fastq files and SAV.tar.fz file are stored (the SAV file includes the Samplesheets and other documents required for the Illumina SAV tool)
# c) thumbnail files (a single tar.gz file): example: ${RUN-FOLDER-NAME}.tumbnails.tar.tgz
# all 3 files are required to obtain the entire RUN-Folder (note the SAV files are stored twice)
# #############################################
# #############################################

# #############################################

# constants
SHOCK_SERVER="http://shock.metagenomics.anl.gov"
TMP_TAR_FILE="/var/tmp/temporary-tar-file-shock-client.$$.tar.gz"

# these functions to be use by all scripts 

# make sure all files are deleted if we exit prematurely or die
function clean_up {

	# Perform program exit housekeeping
	rm -f ${TMP_TAR_FILE}
	exit
}
trap clean_up SIGHUP SIGINT SIGTERM


# securely write filename to SHOCK using the JSON information
# note that the env variable AUTH will provide the authentication 
function secure_shock_write {
	JSON=$1
	FILENAME=$2
	
	echo "uploading ${FILENAME} .. "
								
		# with file, without using multipart form (not recommended for use with curl!)
		JSON=`curl --progress-bar -X POST -H "${AUTH}" -F "attributes_str=${JSON}" -F "upload=@${FILENAME}" ${SHOCK_SERVER}/node`
		# parse the return JSON to find error
		ERROR_STATUS=`echo ${JSON} | jq -r  '{ error: .error }' |  IFS='}' cut -d: -f2 | tr -d "}{\n\"\ "  `
		# grab nodeid from JSON return
			
		NODE_ID=`echo ${JSON} | jq -r ' { nid: .data.id }' |  IFS='}' cut -d: -f2 | tr -d "}{\n\"\ " `
				
		# if there is no return JSON and or we see an error status we report and die
    if [  ${NODE_ID} == "" ]
			then
				echo "can't get a node id (${FILENAME})"
				exit 1		
		fi
		
		# if there is no return JSON and or we see an error status we report and die
    if [  "${JSON}" == ""  -o   "${ERROR_STATUS}" != "null"  ]
			then
				echo "can't get feedback for upload (${FILENAME}, ${ERROR_STATUS})"
				exit 1		
		fi

		echo "done."

		echo "Validating MD5 checksum ... \c"
		# get MD5 for node ID and validate with local md5
		NODE_ATTRIBUTES=`curl -s -X GET  -H "${AUTH}" "http://shock.metagenomics.anl.gov/node/${NODE_ID}" `
		SHOCK_MD5=`echo ${NODE_ATTRIBUTES} | jq -r '{ md5: .data.file.checksum.md5 }' |  IFS='}' cut -d: -f2 | tr -d "}{\n\"\ " `
		
		if [[ ${SHOCK_MD5} == "" ]] # this needs to check for the correct shock response (status 200?)
		then
			echo "$0 could not obtain md5 sum for SHOCK node ${nodeid}"
			exit 1
		fi
		
		# note this will need to be changed when not running on a Mac 
		FILE_MD5=`md5 -q ${FILENAME}`		
		#FILE_MD5=`md5sum $i` # for Linux
		if [[ ${FILE_MD5} != ${SHOCK_MD5} ]]
				then
					echo "$0 MD5 checksum mismatch for ${FILENAME}, aborting (local-md5:(${FILE_MD5}), remote-md5:(${SHOCK_MD5})"
					exit 1	
		fi
		
		echo "done"
	}

# #############################################
# #############################################


rm -f ${TMP_TAR_FILE}


function usage () { 
	echo "Usage: shock-push.sh [-h <help>] [-d] -r <run folder> "
	echo " -d  delete files after upload"
 }

# get options
while getopts hdr: option; do
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
	#    group        project      sample    name
	group=`echo $i | awk -F/  '{print $2 }' `
	project=`echo $i | awk -F/  '{print $3 }' | sed s/Project_//g`
	sample=`echo $i | awk -F/  '{print $4 }' | sed s/Sample_//g`
	file=`echo $i | awk -F/  '{print $5 }' `

	JSON="	{  \
\"type\" : \"run-folder-archive-fastq\" , \
\"run-folder\" : \"${RUN_FOLDER_NAME}\" , \
\"owner\" : \"ANL-SEQ-Core\" , \
\"group\" : \"$group\", \
\"project\" : \"$project\",\
\"sample\" : \"$sample\",\
\"name\" : \"$file\"\
}" 

secure_shock_write "${JSON}" "${i}" 

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
\"owner\" : \"ANL-SEQ-Core\" \
}" 
	
secure_shock_write "${JSON}" "${TMP_TAR_FILE}"
						



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
 







