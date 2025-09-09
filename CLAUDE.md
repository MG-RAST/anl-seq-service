# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

The ANL Sequencing Service is a bioinformatics pipeline for processing Illumina sequencing data. It handles BCL to FASTQ conversion, data upload to SHOCK storage, and SRA (Sequence Read Archive) submissions. The service is containerized and designed to run both as standalone scripts and Docker containers.

## Architecture

### Core Components

- **bin/**: Shell scripts for sequencing workflow execution
  - `master-script.sh`: Main BCL to FASTQ conversion orchestrator
  - `SHOCK_functions.sh`: Reusable functions for SHOCK data storage API interactions
  - `PROJECT_settings.sh`: Project-wide configuration settings
  - Various `shock-*.sh` scripts for data transfer operations

- **lib/**: Libraries in Go and Python
  - `lib/go/`: Go module (v1.15) with node management functionality
  - `lib/python/`: Python classes for run folder management and SRA operations
    - `RunFolder.py`: Manages sequencing run folder metadata
    - `SRA.py`: Main entry point for SRA submission workflows

- **Docker/**: Multi-platform container configurations
  - `base.dockerfile`: Base container for anl-seq-service
  - `Freyja.dockerfile`: Specialized container for Freyja analysis
  - `build-anl-seq-service.sh`: Multi-arch build script for containers

### Data Flow

1. Input: Illumina sequencing run folders with BCL files
2. Processing: BCL to FASTQ conversion using bcl2fastq2
3. Storage: Upload to SHOCK distributed storage system
4. Output: FASTQ files and metadata for downstream analysis

## Development Commands

### Docker Operations

Build multi-architecture containers:
```bash
# Build and push latest version
cd Docker && ./build-anl-seq-service.sh

# Build specific containers
docker build --platform linux/amd64 -t Freyja:latest -f Freyja.dockerfile .
```

### Main Service Operations

Run BCL to FASTQ conversion:
```bash
# Basic usage
bin/master-script.sh -i <input_dir> -o <output_dir> -s <sample_sheet>

# With additional options
bin/master-script.sh -i <input_dir> -o <output_dir> -s <sample_sheet> -m -t s_1
```

Run SRA submission (main Docker entry point):
```bash
python3 lib/python/SRA.py --help
```

### SHOCK Storage Operations

The service integrates with SHOCK (distributed storage system) through functions in `bin/SHOCK_functions.sh`:

- Authentication via `/usr/local/share/anl-seq-service/auth.env`
- MD5 checksum validation for uploads
- Duplicate file detection
- Metadata management through JSON attributes

## Configuration

### Environment Variables
- `AUTH`: SHOCK authentication header (loaded from auth.env)
- `SHOCK_SERVER`: SHOCK server URL
- `OWNER`: Set to "ANL-SEQ-Core" in project settings

### Key Settings
- Default thread count: 8
- Supported data types: run-folder-archive-thumbnails, run-folder-archive-fastq, run-folder-archive-sav, run-folder-archive-raw
- Adapter files located in `share/adapter-directory/`

## Dependencies

### Container Dependencies
- Ubuntu base image
- bcl2fastq2 (Illumina BCL conversion tool)
- Python 3 with pysftp, cwlref-runner
- Standard bioinformatics tools: bowtie2, idba
- System utilities: jq, curl, wget

### Go Dependencies
- Go 1.15
- github.com/go-delve/delve v1.6.0 (debugging)

## Special Notes

- All SHOCK uploads include MD5 validation
- The service supports various Illumina index configurations (Nextera, TruSeq, dual index)
- Scripts are designed for both single and paired-end sequencing runs
- Container entry point defaults to SRA.py with --help
- Authentication credentials must be properly configured in auth.env for SHOCK operations