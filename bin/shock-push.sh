#!/bin/bash
# this script pushes a run folder to shock, removing all unneeded parts (PLEASE NOTE: the base calls are a separate SHOCK node)
# the run folder will be pruned, tar'ed and moved as one tar.gz file

# constants
SHOCK-SERVER=http://shock.metagenomics.anl.gov
TMP-TAR-FILE=/var/tmp/temporary-tar-file-shock-client.$$.tar.gz

rm -f ${TMP-TAR-FILE}



usage () { 
	echo "Usage: shock-pull.sh [-h <help>] -r <run folder> "

 }

# get options
while getopts hr: option; do
    case "${option}"
        in
            h) 	HELP=1;;
            r) 	RUN-FOLDER=${OPTARG};;
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


# 
echo "pruning goes here, to be added later after discussing with SARAH"


echo "tar and gzip goes here"
return=`tar cfz ${TMP-TAR-FILE} ${RUN-FOLDER} `
if [[ $return != 0 ]]
then
	echo "$0 tar command failed [ $? ] "
	rm -f ${TMP-TAR-FILE}
fi

RUN-FOLDER-NAME=`basename ${RUN-FOLDER}`

# with file, without using multipart form (not recommended for use with curl!)
curl -X POST -F 'attributes_str={ "RUN-FOLDER : ''${RUN-FOLDER-NAME}" ''}' \
			 -F 'attributes_str={ "type" : "run-folder-archive"}' \
				 -F 'attribute_str={ "Organzation" : "ANL-SEQ-Core" }' \
		     --data-binary @<path_to_data_file> ${SHOCK-SERVER}/node




