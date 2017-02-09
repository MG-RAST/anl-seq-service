#!/bin/bash


# # this script pushes a run folder to shock, creating 3 different subsets
# 
# a) entire run folder (minus fastq files and minus thumbnails); a single tar.gz file ${RUN-FOLDER-NAME}.tar.gz
# b) multiple fastq files and SAV.tar.fz file are stored (the SAV file includes the Samplesheets and other documents required for the Illumina SAV tool)
# c) thumbnail files (a single tar.gz file): example: ${RUN-FOLDER-NAME}.tumbnails.tar.tgz
# all 3 files are required to obtain the entire RUN-Folder (note the SAV files are stored twice)


# constants
SHOCK-SERVER=http://shock.metagenomics.anl.gov
TMP-TAR-FILE=/var/tmp/temporary-tar-file-shock-client.$$.tar.gz
AUTH=

rm -f ${TMP-TAR-FILE}


usage () { 
	echo "Usage: shock-push-raw.sh [-h <help>] [-d] -r <run folder> "
    echo " -d  delete files after upload"
 }

# get options
while getopts hr: option; do
    case "${option}"
        in
            h) 	HELP=1;;
            r) 	RUN-FOLDER=${OPTARG};;
			d)  DELETE=1;;
		*)
			usage
			;;
    esac
done

# 
if [[ ! -d ${RUN-FOLDER} ] ]
then
	echo "$0 ${RUN-FOLDER} not found"
	usage()
	exit 1
fi

# check for presence of RTAComplete.txt
if [[ ! -e ${RUN-FOLDER}/RTAComplete.txt] ]
then
	echo "$0 ${RUN-FOLDER} is incomplete, RTAComplete.txt is not present. Aborting"
	exit 1
fi	 

# strip the prefix of the run folder to get the name 
RUN-FOLDER-NAME=`basename ${RUN-FOLDER}`

# terminate on error
set -e

# fastq files
cd ${RUN-FOLDER}

# build a list of files excluding Thumbnails, FASTQs and SAV files
FILES=`find ./| fgrep -v fastq  | fgrep -v Thumbnail_Image | fgrep -v InterOp | fgrep -v RunInfo.xml | fgrep -v runParameters.xml | fgrep -v Samplesheet.csv `

res=`tar cvfz ${TMP_TAR_FILE} ${FILES}`

if [ !$? -eq 0 ]
then 
  echo "$0 Could not create raw tar file " >&2
  exit 1	
fi

# with file, without using multipart form (not recommended for use with curl!)
JSON="attributes_str={ \"run-folder\" : ${RUN-FOLDER-NAME},  \"type\" : "run-folder-archive-raw", \"name\" : \"${RUN-FOLDER}.raw.tar.gz\", \"organization\" : \"ANL-SEQ-Core\" }"

#curl -X POST ${AUTH} -F ${JSON} --data-binary ${TMP_TAR_FILE} ${AUTH} ${SHOCK-SERVER}/node

# clean up
rm -f ${TMP_TAR_FILE}

if [[ ${DELETE} == "1" ]]
then
	echo "removing all files except FASTQ, SAV and Thumbnails in 5 seconds [time for CTRL-C now...]"
	sleep 5
#	rm -rf ${FILES}Thumbnail_images
fi






