# Dockerfile for influenza_a_serotype
# https://github.com/mtisza1/influenza_a_serotype

FROM continuumio/miniconda3:latest

LABEL maintainer="Andreas Wilke"
LABEL maintainer.email="wilke@anl.gov"
LABEL description="Docker image for influenza_a_serotype"
LABEL version="0.1.5"
LABEL github="https://github.com/mtisza1/influenza_a_serotype"
LABEL build-date=""

# Set non-interactive mode for apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
USER root
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    tar \
    gzip \
    unzip \
    build-essential \
    less \
    vim \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a directory for data
RUN mkdir -p /data

# Set working directory
WORKDIR /app

# Create a non-root user
RUN useradd -ms /bin/bash condauser
RUN chown -R condauser:condauser /app && \
    chown -R condauser:condauser /data
    # chown -R condauser:condauser /opt/conda && \
    # chmod -R 755 /opt/conda && \
    

# Set the PATH for the conda environment
# Set the user to the non-root user
USER condauser

# Clone the repository
# git@github.com:wilke/influenza_a_serotype.git
RUN git clone https://github.com/wilke/influenza_a_serotype.git /app/influenza_a_serotype && \
    cd /app/influenza_a_serotype && \
    git checkout wilke/chunk

# # Create the conda environment from the YAML file in the repository
RUN conda env create -f /app/influenza_a_serotype/environment/iav_serotype.yaml && \
    conda clean -a -y

# RUN sed 's/^ *- *python=.*$/  - python/' /app/influenza_a_serotype/environment/iav_serotype.yaml > /tmp/env.yaml && \
#     conda env create -f /tmp/env.yaml && \
#     conda clean -a -y

# Set up environment activation in bashrc
RUN echo "conda activate iav" >> ~/.bashrc

# Install the repository
SHELL ["/bin/bash", "-c"]
RUN source /opt/conda/etc/profile.d/conda.sh && \
    conda activate iav && \
    cd /app/influenza_a_serotype && \
    pip install .

# Create directory for database files
RUN mkdir -p /app/DBs/v1.25

# Download and extract the database files
RUN source /opt/conda/etc/profile.d/conda.sh && \
    conda activate iav && \
    cd /app && \
    wget https://zenodo.org/records/11509609/files/Influenza_A_segment_sequences.tar.gz && \
    tar -xvf Influenza_A_segment_sequences.tar.gz && \
    rm Influenza_A_segment_sequences.tar.gz

# Set environment variable for database location
ENV IAVS_DB=/app/DBs/v1.25

# Create a directory for input/output data
RUN mkdir -p /data

# Set the working directory to /data for mounting volumes
WORKDIR /data

# Set the entrypoint to run iav_serotype
ENTRYPOINT ["/bin/bash", "-c", "source /opt/conda/etc/profile.d/conda.sh && conda activate iav && iav_serotype \"$@\"", "--"]

# Default command shows help
CMD ["--help"]