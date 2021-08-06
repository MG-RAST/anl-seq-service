#!/bin/bash

#  add the rundate to all folders in shock

# constants
SHOCK_SERVER="http://shock.metagenomics.anl.gov"
TMP_TAR_FILE="/var/tmp/temporary-tar-file-shock-client.$$.tar.gz"

set -o allexport
source ../auth.env
set +o allexport

# make sure all files are deleted if we exit prematurely or die
function clean_up {

        # Perform program exit housekeeping
        rm -f ${TMP_TAR_FILE}
        exit
}
trap clean_up SIGHUP SIGINT SIGTERM

rm -f ${TMP_TAR_FILE}

function usage { 
echo " add rundate from run_folder name / project_id"
echo "Usage: $0 [-h <help>] "
 }

# get options
while getopts h option; do
    case "${option}"
        in
                h) HELP=1;;
                *)
                usage
                ;;
    esac
done

#init our file counter
counter=0

# exit on any error
set -e 

#JSON=$(curl --silent -X GET -H "${AUTH}" "${SHOCK_SERVER}/node?query&type=run-folder-archive-fastq" )
JSON=$(curl --silent -X GET -H "${AUTH}" "${SHOCK_SERVER}/node?query&limit=25000&type=run-folder-archive-fastq" )

# get a list of nodes
IDS=$( echo ${JSON} | jq '  .data[].id ' )

for i in ${IDS}
do
        j=$(echo ${i} | tr -d \" )
        RETURN=$(curl --silent -X GET -H "${AUTH}" "${SHOCK_SERVER}/node/${j}")
        PROJ=$(echo ${RETURN}  | jq '  .data.attributes.project_id  ' )
        NEWDAT=$(echo ${PROJ} | cut -d_ -f1 | tr -d '"')
        rundate="20${NEWDAT}"
        NEWJSON1=$(echo ${RETURN} | jq ' { name: .data.file.name  }  +  { project_id: .data.attributes.project_id } + { owner: .data.attributes.owner } + { project: .data.attributes.project } + { group: .data.attributes.grou
p } + { sample: .data.attributes.sample } + { type: .data.attributes.type}')
        NEWJSON=$(echo ${NEWJSON1} | sed -e "s/ }$/,\"rundate\": \"${rundate}\" }/")
        echo ${NEWJSON} > /tmp/outfile.json
        retu=$(curl --silent -X PUT -H "${AUTH}" -F "attributes=@/tmp/outfile.json" "${SHOCK_SERVER}/node/${j}")
        echo $counter
        counter=$((counter+1))
done


