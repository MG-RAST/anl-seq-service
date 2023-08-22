# Docker file for the Argonne Sequencing service

FROM	ubuntu:22.04
LABEL MAINTAINER="wilke@anl.gov"

ARG TARGETPLATFORM
ARG BUILDPLATFORM
RUN echo "I am running on $BUILDPLATFORM, building for $TARGETPLATFORM" > /log

RUN apt-get update -y
RUN apt-get update -y --fix-missing
RUN apt install -y \
   alien \
   bowtie2 \
   build-essential\
   curl \
   dh-autoreconf \
   idba \
   jove \
   jq \
   less \
   python3\
   python3-setuptools \
   python3-pip\
   unzip \
   vi \
   wget 
  


# download URL for the version 2.18 of the Illumina software
ADD https://support.illumina.com/content/dam/illumina-support/documents/downloads/software/bcl2fastq/bcl2fastq2-v2-19-1-linux.zip /root/bcl2fastq2.zip
RUN if [ "$TARGETPLATFORM" = "linux/amd64" ]; then cd /root ; unzip /root/bcl2fastq2*.zip ; alien -i /root/bcl2fastq2-*.rpm ; else touch /arm64.found ; fi
# http://support.illumina.com/content/dam/illumina-support/documents/downloads/software/bcl2fastq/bcl2fastq2-v2-18-0-12-linux-x86-64.zip

# RUN  (cd /root ; unzip /root/bcl2fastq2*.zip ;)
# RUN alien -i /root/bcl2fastq2-*.rpm


# # copy local files to /usr/local/ (binaries and adapter files)
# ADD bin/* /usr/local/bin/
# ADD share/* /usr/local/share/

# install CWL runner
RUN pip3 install --upgrade pip && \
     pip3 install cwlref-runner


COPY . /anl-seq-service
