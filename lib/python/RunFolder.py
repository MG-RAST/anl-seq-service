import json
import yaml
import logging
import os
import glob
import re
import shutil
import subprocess
import sys
from pprint import pprint

# Setup logging
logger = None
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class RunFolder():

       def __init__(self,   owner='TESTER' , 
                            file=None , 
                            project=None , 
                            project_id=None , 
                            group=None ,
                            sample = None , 
                            id=None):

            self.id         = id
            self.type       = "run-folder-archive-fastq"
            self.project_id = project_id    # ${RUN_FOLDER_NAME}" 
            self.owner      = owner         # "${OWNER}", 
            self.group      = group  
            self.project    = project
            self.sample     = sample
            self.name       = file
            self.tags       = []
                    
            
           
            
   