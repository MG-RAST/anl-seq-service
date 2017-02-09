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
	echo "Usage: shock-push.sh [-h <help>] [-d] -r <run folder> "
    echo " -d  delete files after upload"
 }

# get options
while getopts hr: option; do
    case "${option}"
        in
            h) 	HELP=1;;
            r) 	RUN-FOLDER=${OPTARG};;
			d) DELETE=1;;	leave for later
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


# exit on any error
set -e 

# strip the prefix of the run folder to get the name 
RUN-FOLDER-NAME=`basename ${RUN-FOLDER}`

# fastq files
cd ${RUN-FOLDER}
FASTQ-FILES=`find ./ -name \*.fastq\*`
for i in ${FASTQ-FILES}
do
	echo $i

	# use Illumina directory structure to extract group (e.g. unaligned), project and sample info.
	# ./unaligned/Project_AR3/Sample_AR314/AR314_GGAACT_L003_R1_001.fastq.gz  [sample $i]
	echo $i | awk -F/  '{print $2 $3 $4 $5}' | while read  group project sample file
	do
		JSON="	{ \"run-folder\" : \"${RUN-FOLDER-NAME}\" , \
				  \"type\" : \"run-folder-archive-fastq\" , \
   			 	\"group\" : \"$group\", \
				\"project\" : \"$project\",\		
				\"sample\" : \"$sample\",\
				\"name\" : \"$file\",\	
				\"organization\" : \"ANL-SEQ-Core\" }" 
								
		# with file, without using multipart form (not recommended for use with curl!)
#		curl -X POST ${AUTH} -F "attributes_str=${JSON}" --data-binary $i  ${SHOCK-SERVER}/node
echo ${JSON}
echo $i
	done
done


# find SAV files now and tar them

# from documentation SAV files are:  RunInfo.xml, runParameters.xml, SampleSheet.csv, InterOP  (directory)
cd ${RUN-FOLDER}
SAV-FILES="RunInfo.xml runParameters.xml SampleSheet.csv InterOP"

return=`tar cfz ${TMP-TAR-FILE} ${SAV-FILES} `
if [[ $return != 0 ]]
then
	echo "$0 tar command failed [ $? ] "
	rm -f ${TMP-TAR-FILE}
fi

JSON="	{ \"run-folder\" : \"${RUN-FOLDER-NAME}\" , \
		  \"type\" : \"run-folder-archive-sav\" , \
		\"name\" : \"${RUN-FOLDER-NAME}-sav.tar.gz\" ,\	
		\"organization\" : \"ANL-SEQ-Core\" }" 
						
# with file, without using multipart form (not recommended for use with curl!)
curl -X POST ${AUTH} -F "attributes_str=${JSON}" --data-binary ${TMP-TAR-FILE}  ${SHOCK-SERVER}/node

if [[ ${DELETE-FILES} == "1" ]]
	then	
		cd ${RUN-FOLDER}
		echo "removing FASTQ + SAV files in 5 seconds [time for CTRL-C now...]"
		sleep 5
		# rm -rf ${SAV-FILES} ${FASTQ-FILES}
	fi
	
# cleanup
exit 1
rm -f ${TMP-TAR-FILE}
 







