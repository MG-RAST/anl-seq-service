#!/bin/bash

# Define the singularity image path
SINGULARITY_IMAGE="/nfs/seq-data/images/bcl2fastq_2.20.0.sif"

# Initialize variables
INPUT_DIR=""
ARGS=()

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --input-dir)
            INPUT_DIR="$2"
            shift 2
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

# Check if input directory is set
if [[ -z "$INPUT_DIR" ]]; then
    echo "Error: --input-dir is not set."
    exit 1
fi

# Get the current working directory
CWD=$(pwd)

# Execute the bcl2fastq command inside the singularity container
singularity exec --bind "$CWD":"$CWD" --bind "$INPUT_DIR":"$INPUT_DIR" "$SINGULARITY_IMAGE" bcl2fastq "${ARGS[@]}"