#!/bin/bash 

#constants
SHOCK_SERVER="http://shock.mg-rast.org"
TMP_DIR=/tmp
OWNER=ANL-SEQ-Core

TOKEN=$TOKEN
BEARER=seqcenter
USER_TOKEN=
GROUP=
PROJECT=
PROJECT_ID=

 # get options
while getopts :h:p:g:i:l: option; do
    case "${option}"
        in
		h) HELP=1;;
        p) PROJECT=${OPTARG};;
        g) GROUP=${OPTARG};;
        i) PROJECT_ID=${OPTARG};;
        l) LIST=1;;
		*)
		echo Found nothing
		;;
    esac
done

echo $LIST
echo PROJECT: $PROJECT

QUERY="?query&owner=${OWNER}"
if [ ! -z ${PROJECT} ] ; then
    QUERY="${QUERY}&project=${PROJECT}"
fi

if [ ! -z ${PROJECT_ID} ] ; then
    QUERY="${QUERY}&project_id=${PROJECT_ID}"
fi

if [ ! -z ${GROUP} ] ; then
    QUERY="${QUERY}&group=${GROUP}"
fi

# echo $QUERY

# curl -L -H "Authorization: $BEARER $TOKEN" "${SHOCK_SERVER}/node/${QUERY}" | tee ${TMP_DIR}/tmp.json | jq 
echo $QUERY
LIMIT=`curl -L -H "Authorization: $BEARER $TOKEN" "${SHOCK_SERVER}/node/${QUERY}" | jq .total_count` 
5echo curl -L -H \"Authorization: $BEARER $TOKEN\" \"${SHOCK_SERVER}/node/${QUERY}\" 
echo LIMIT=${LIMIT}

# curl -L -H "Authorization: mgrast $TOKEN" "${SHOCK_SERVER}/node?query&project=230614_Wall_Run3_demultiplxed&project_id=230614_M02149_0020_000000000-KRCNF&owner=ANL-SEQ-Core&limit=500" > ${TMP_DIR}/tmp.json 


curl -L -H "Authorization: $BEARER $TOKEN" "${SHOCK_SERVER}/node/${QUERY}&limit=${LIMIT}" | tee  tmp.json | jq -r ".data[] | [ .id , .attributes.project_id , .attributes.project , .attributes.group , .file.name] | @tsv" | tee ids.tmp
# cat tmp.json | jq -r ".data[] | [ .id , .attributes.project_id , .attributes.project , .attributes.group , .file.name] | @tsv"

for i in `cat tmp.json | jq -r ".data[] | [ .id , .attributes.project_id , .attributes.project , .file.name] | @tsv" | cut -f1,4 --output-delimiter="," ` ; do  
    id=`echo $i | cut -f1 -d ","` ; 
    fn=`echo $i | cut -f2 -d ","` ; 
    echo curl -o $fn -L -H \"Authorization: seqcenter ZHuL913LScivanXGx2N7M1g5YFnZV7wP\" \"http://shock.mg-rast.org/node/${id}?download\" ; 
    echo wget -O ${fn} --header \"Authorization: ${BEARER} ${TOKEN}\" \"${SHOCK_SERVER}/node/${id}?download\" ;
done > download_list.${PROJECT}.txt
