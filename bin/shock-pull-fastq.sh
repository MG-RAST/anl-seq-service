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
		h) HELP=1;;
		r) RUN_FOLDER=${OPTARG};;
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
# use the JQ tool to parse the correct IDs for the SHOCK objects from the return JSON struct 
#    the correct invocation is --> jq -r '{ data: .data[].id  } '  <-- 

FASTQ_FILES_JSON="
curl -X GET "http://shock.metagenomics.anl.gov/node/order=created_on&direction=desc&offset=0&querynode&attributes.data_type=run-folder-archive-fastq&run-folder=${RUN_FOLDER_NAME}" -H 'Host: shock.metagenomics.anl.gov' -H 'Accept: application/json, text/javascript, */*; q=0.01' ${AUTH}"

# sample jq output
# {
#  "data": "5c44f98b-a83f-4320-ac30-abdcad64c7fa",
#  "name": "error",
#  "md5": "b0343349b7f7b3ab6550c649a3299a9d",
#  "length": 376,
#  "owner": "anonymous"
# }

#FASTQ_FILES_IDS=echo "${FASTQ_FILES_JSON}" | jq -r '{ data: .data[].id  } ' | tr -d " {}\"" | fgrep data | cut -f2 -d:
#USE JQ to parse JSON install via "wget -O jq https://github.com/stedolan/jq/releases/download/jq-1.5/jq-linux64"

# parse filename, project, group, sample , md5 and length from JSON struct
PARSED_JSON= `echo ${FASTQ_FILES_JSON} | jq -r '{ data: .data[] .id , name: .data[].file.name , md5: .data[].file.checksum.md5 , length: .data[].file.size, project: .data[].attributes.project , group: .data[].attributes.group , sample: .data[].attributes.sample}  ' |  awk '  BEGIN { RS="\}" } { print  $3 $5 $7 $9 } ' ` | tr -d "\" `

for i in ${PARSED_JSON}
do

	file=`echo $i | awk -F/  '{print $1 }'  `
	filename=`echo $i | awk -F/  '{print $2 }'  `
	md5=`echo $i | awk -F/  '{print $3 }'  `
	group=`echo $i | awk -F/  '{print $2 }' `
	sample="Sample_"`echo $i | awk -F/  '{print $4 }' | sed s/Sample_//g`
	project="Project_"`echo $i | awk -F/  '{print $3 }' | sed s/Project_//g`

	mkdir -p ${sample}/${project}/${sample}
	set -e
	res=`curl ${AUTH} --data-binary $i  ${SHOCK-SERVER}/node > ${filename}`

	if [[ $res != 0 ]]
		then
			echo "download failed ($filename)"
			exit 1
	fi
	set +e

done


	# use Illumina directory structure to extract group (e.g. unaligned), project and sample info.
	# ./unaligned/Project_AR3/Sample_AR314/AR314_GGAACT_L003_R1_001.fastq.gz  [sample $i]
		
	group=`echo $i | awk -F/  '{print $2 }' `
	project=`echo $i | awk -F/  '{print $3 }' | sed s/Project_//g`
	sample=`echo $i | awk -F/  '{print $4 }' | sed s/Sample_//g`
	file=`echo $i | awk -F/  '{print $5 }' `

	JSON="	{ \"organization\" : \"ANL-SEQ-Core\" , \
		 		\"run-folder\" : \"${RUN_FOLDER_NAME}\" , \
				\"type\" : \"run-folder-archive-fastq\" , \
   			 	\"group\" : \"$group\", \
				\"project\" : \"$project\",\		
				\"sample\" : \"$sample\",\
				\"name\" : \"$file\"
				}" 
								
		# with file, without using multipart form (not recommended for use with curl!)
#		curl -X POST ${AUTH} -F "attributes_str=${JSON}" --data-binary $i  ${SHOCK-SERVER}/node
	echo ${JSON}

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







