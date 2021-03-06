# Docker file for the Argonne Sequencing service

FROM	ubuntu
MAINTAINER folker@anl.gov

RUN apt-get update -y
RUN apt-get update -y --fix-missing
RUN  apt-get install -y \
   alien \
   bowtie2 \
   build-essential\
   curl \
   dh-autoreconf \
   idba \
   jove \
   python \
   python-setuptools\
   python-pip\
   unzip \
   wget 
  


  # download URL for the version 2.18 of the Illumina software
# http://support.illumina.com/content/dam/illumina-support/documents/downloads/software/bcl2fastq/bcl2fastq2-v2-18-0-12-linux-x86-64.zip
ADD https://support.illumina.com/content/dam/illumina-support/documents/downloads/software/bcl2fastq/bcl2fastq2-v2-19-1-linux.zip /root/bcl2fastq2.zip
RUN  (cd /root ; unzip /root/bcl2fastq2*.zip )
RUN alien -i /root/bcl2fastq2-*.rpm


# copy local files to /usr/local/ (binaries and adapter files)
ADD bin/* /usr/local/bin/
ADD share/* /usr/local/share/

# install CWL runner
RUN pip install --upgrade pip && \
     pip install cwlref-runner

