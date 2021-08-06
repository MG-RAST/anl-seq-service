#!/usr/bin/env cwl-runner

cwlVersion: v1.1
class: Workflow

label: archive-run-folder

doc: |
    process run folder

requirements:
    StepInputExpressionRequirement : {}
    ScatterFeatureRequirement: {}
    InlineJavascriptRequirement : {}

# hints: 

inputs:
    # projects: string
    fastq-files: File[]
    mapping-files: File[]

steps:
    create-shock-index:
        scatter: fastq
        scatterMethod: dotproduct
        run: ../Tools/fastq2byte_index.cwl
        in:
            fastq: fastq-files
            binary_index:
                valueFrom: $(inputs.fastq.nameroot).idx
            record_index:
                valueFrom: $(inputs.fastq.nameroot).rec
            id2rec_index:
                valueFrom: $(inputs.fastq.nameroot).id2rec


        out: [ info , error , idx , record , id2rec ]

    demultiplex2index:
        run: ../Tools/demultiplex2index.cwl
        scatter: [ input , barcode]
        scatterMethod: dotproduct
        in:
            input: fastq-files
            barcode: mapping-files
        out: [ info , error , samples ]

    make_demux_return:
        run:
            cwlVersion: v1.1
            class: ExpressionTool
            inputs:
                info:
                    type: File[]
                error:
                    type: File[]
                samples: 
                    type: 
                        type: array
                        items: 
                            - type: array
                              items: File
            outputs:
                demux:
                    type: Any
            expression: |
                ${
                    var demux = {
                        "info" : inputs.info ,
                        "error" : inputs.error ,
                        "samples" : inputs.samples ,
                        };
                    return { 'demux' : demux } ;
                }

        in:
            info: demultiplex2index/info
            error: demultiplex2index/error
            samples: demultiplex2index/samples
        out: [demux]

outputs:
    info:
        type: File[]
        outputSource: create-shock-index/info
    error:
        type: File[]
        outputSource: create-shock-index/error
    idx:
        type: File[]
        outputSource: create-shock-index/idx
    record:
        type: File[]
        outputSource: create-shock-index/record
    id2rec:
        type: File[]
        outputSource: create-shock-index/id2rec
    demux:
        type: Any
        outputSource: make_demux_return/demux
        
        
    #             outputBinding:
    #                 glob: bar
    # # demux:
    #     type: 
    #         type: record
    #         name: a
    #         fields: 
    #             - name: info
    #               type: File[]
    #               outputBinding: 
    #                 valueFrom: $(self[0])
                # - error:
                #     type: File[]
                #     outputSource: demultiplex2index/error
                # samples:
                #     type: array
                #     items: 
                #         - type: array
                #           items: File
                #     outputSource: demultiplex2index/samples
        # outputSource: [ demultiplex2index/info , demultiplex2index/error , demultiplex2index/samples ]