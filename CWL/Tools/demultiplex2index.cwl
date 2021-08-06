#!/usr/bin/env cwl-runner

cwlVersion: v1.1
class: CommandLineTool

label: demultiplex2index
doc: |
    Demultiplexes a fastq file and creates subset indices
   

hints:
    DockerRequirement:
        dockerPull: mgrast/pipeline:4.04

requirements:
    InlineJavascriptRequirement: {}
    InitialWorkDirRequirement :
        listing:
            - $(inputs.input)
            - $(inputs.barcode)


stdout: demux2i.log
stderr: demux2i.error

inputs:
    input:
        type: File
        doc: fastq or fasta file
        inputBinding:
            prefix: --input

    format:
        type: 
            type: enum
            symbols:
                - fasta
                - fastq
            inputBinding:
                prefix: --format    
        doc: sequence type
        default: fastq
    
    barcode:
        type: File
        doc: barcode/mapping file
        inputBinding:
            prefix: --barcode
    
    reverse:
        type: boolean?
        doc: name for record_index file
        inputBinding:
            prefix: --rc_bar


baseCommand: [demultiplex2index.py]

# arguments:
#     - None
      
outputs:

    info:
        type: stdout

    error: 
        type: stderr

    samples:
        type: File[]
        doc: id to record  index
        outputBinding:
            glob: "*.fastq"


