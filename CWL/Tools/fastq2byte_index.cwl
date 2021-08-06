#!/usr/bin/env cwl-runner

cwlVersion: v1.1
class: CommandLineTool

label: fastq2idx
doc: |
    Creates a record byte index for a fastq file. This index can be uplaoded as uploaded to shock as shock index for the fastq file.
   

hints:
    DockerRequirement:
        dockerPull: mgrast/pipeline:4.04

requirements:
    InlineJavascriptRequirement: {}

stdout: f2i.log
stderr: f2i.error

inputs:
    fastq:
        type: File
        doc: fastq file
        inputBinding:
            prefix: --input
    
    binary_index:
        type: string
        doc: name for binary_index file
        default: tmp.idx
        inputBinding:
            prefix: --index
    
    record_index:
        type: string
        doc: name for record_index file
        default: tmp.rec
        inputBinding:
            prefix: --record
    
    id2rec_index:
        type: string
        doc: name for id2rec_index file, creates a sequence id to record mapping
        default: tmp.id2rec
        inputBinding:
            prefix: --id2rec
    
    


baseCommand: [fastq2byte_idx.py]

# arguments:
#     - None
      
outputs:

    info:
        type: stdout

    error: 
        type: stderr

    idx:
        type: File
        doc: binary index
        outputBinding: 
            glob: $(inputs.binary_index)

    record:
        type: File
        doc: record index
        outputBinding: 
            glob: $(inputs.record_index)

    id2rec:
        type: File
        doc: id to record  index
        outputBinding: 
            glob: $(inputs.id2rec_index)

