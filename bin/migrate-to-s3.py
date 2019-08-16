#!/usr/bin/env python3

import argparse
import datetime
import glob
import importlib
import json
import logging
import os
import pymongo
import random
import re
import requests
import subprocess

import sys
import time
# import yaml
import shutil

from uuid import getnode as get_mac
from subprocess import Popen, PIPE
from bson import json_util
from urllib.parse import quote_plus



def download_and_upload(node) :
    # download
    print("Downloading " + node['id'] )
    file_name = node['id'] + ".data"

    download_url = base_url + "/" + node['id'] + "?download"
    s3uri = 's3://anlseq/' + file_name

    with requests.get(download_url , headers=headers, stream=True) as response :
        with open( file_name , mode='wb') as localfile:   
            shutil.copyfileobj(response.raw, localfile)  
            # localfile.write(response.content)
        
    # push to local s3
    print("Uploading " + entry['id'])
    process = subprocess.run(
        ["s3cmd", "put" , file_name , s3uri ] , capture_output=True )

    # check upload
    process = subprocess.run(
        ["s3cmd", "info" , s3uri ] , capture_output=True )
   
    m = re.search("MD5 sum:\s+([^\s]+)" , process.stdout.decode("utf-8") )
    
    if m[1] == entry['file']['checksum']['md5'] :
        print("Uploaded , same checksum " + file_name )
        # delete local file and update node with location
        os.remove(file_name)
        # update_node()
    else :
        print("\t".join( [ 'ERROR:' , 'checksums not identical' , node['id'] ] ) )
        download_and_upload(entry)


parser = argparse.ArgumentParser()

parser.add_argument("action",
                    choices=['update', 'load', 'drop', 'list', 'test'],
                    type=str,
                    default=None
                    )
parser.add_argument("--host",
                    type=str, dest="host",
                    default="http://localhost",
                    help="shock url")
parser.add_argument("--port",
                    type=str, dest="port",
                    default="",
                    help="shock port")
parser.add_argument("--user",
                    type=str,
                    help="user",
                    default=None)
parser.add_argument("--password",
                    type=str,
                    default=None)
parser.add_argument("--token",
                    type=str,
                    default=None)                    
parser.add_argument("--debug",
                    action="store_true",
                    default=False)
parser.add_argument("--dry-run",
                    action="store_true",
                    default=False)
parser.add_argument("--force",
                    action="store_true",
                    default=False,
                    help="force update")
parser.add_argument("--project",
                    type=str,  
                    default=None,
                    help="force update")





           

args = parser.parse_args() 
host=args.host + "/node"
port=args.port
verbose = False

base_url= host if not port else ":".join([host, port])
query= "query&type=run-folder-archive-fastq" if not args.project else "&".join( ["query" , "type=run-folder-archive-fastq" , "project_id=" + args.project ] )
url = "?".join([ base_url , query])

headers = None
if not args.token or ( args.password and agrs.user) :
    print("Missing credentials, please provide token or user:password")
    sys.exit(1)
elif args.token :
    headers = { 'Authorization' : 'mgrast ' + args.token }
else :
    print( "user:password not supported")
    sys.exit(1)        


print(url)
print(headers)
response = requests.get(url + "&limit=100" , headers=headers)

while response.status_code == 200 :

    envelope = response.json()
    print( "\t".join( [ "Offset: " , str(envelope['offset']) , str(envelope['total_count']) ] ) )

    # do stuff

    for entry in envelope['data'] :
        print("Processing:\t" + entry['id']) 

        # check if id already exists, otherwise upload 
        # s3uri = 's3://anlseq/' + entry['id'] + "/" + entry['id'] + ".data"
        s3uri = 's3://anlseq/' + entry['id'] + ".data"
        process = subprocess.run(
            ["s3cmd", "info" , s3uri ] , capture_output=True )
        # print( process.stdout)
        # print( "Error" + process.stderr.decode("utf-8") )

        if process.stderr :
            if re.search("404" , process.stderr.decode("utf-8") ) :
                # Node not uploaded
                # Get from shock and push to s3

                # download
                download_and_upload(entry)

                # print("Downloading " + entry['id'] )
                # download_url = base_url + "/" + entry['id'] + "?download"
                # with requests.get(download_url , headers=headers, stream=True) as response :
                #     with open( entry['id'], mode='wb') as localfile:   
                #         shutil.copyfileobj(response.raw, localfile)  
                #         # localfile.write(response.content)
                    
                # # push to local s3
                # print("Uploading " + entry['id'])
                # process = subprocess.run(
                #     ["s3cmd", "put" , entry['id'] , s3uri ] , capture_output=True )

                # check and delete 
                # sys.exit(1)
       
        else:
            # check if upload was complete, compare md5sums
            # MD5 sum:   450eb9685cb06ca70382d31aba439e3f
            m = re.search("MD5 sum:\s+([^\s]+)" , process.stdout.decode("utf-8") )

            if m[1] == entry['file']['checksum']['md5'] :
                print("Identical " + entry['id'])
            else :
                print('Not identical, reupload')
                download_and_upload(entry)
        
       



    new_offset = envelope['offset'] + envelope['limit']
    if new_offset < envelope['total_count'] :
        response = requests.get( "&". join( [url , "offset=" + str(new_offset) , "limit=" + str(envelope['limit'] ) ] ) , headers=headers) 
    else :
        break    

    