#!/bin/bash

# Define the singularity image path
SINGULARITY_IMAGE="/nfs/seq-data/images/bcl2fastq_2.20.0.sif"

# Initialize variables
INPUT_DIR=""
ARGS=()

# Initialize sample sheet variable
SAMPLE_SHEET=""

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --input-dir)
            INPUT_DIR="$2"
            ARGS+=("$1")
            ARGS+=("$2")
            shift 2
            ;;
        --sample-sheet)
            SAMPLE_SHEET="$2"
            ARGS+=("$1")
            ARGS+=("$2")
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
    echo "Setting to current working directory: $(pwd)"
    INPUT_DIR=$(pwd)
fi

# Get the current working directory
CWD=$(pwd)

# Execute the bcl2fastq command inside the singularity container
if [[ -z "$SAMPLE_SHEET" ]]; then
    echo singularity run --bind "$CWD":"$CWD" --bind "$INPUT_DIR":"$INPUT_DIR" "$SINGULARITY_IMAGE" "${ARGS[@]}"
else
    echo singularity run --bind "$CWD":"$CWD" --bind "$INPUT_DIR":"$INPUT_DIR" --bind "$SAMPLE_SHEET":"$SAMPLE_SHEET" "$SINGULARITY_IMAGE" "${ARGS[@]}"
fi
