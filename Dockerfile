# Docker file for the Argonne Sequencing service

FROM	centos
MAINTAINER folker@anl.gov


RUN yum update -y && yum install -y \
   epel-release \
   dh-autoreconf \
   epel-release \
   unzip \
   wget \
   python \
   python2-pip \
   emacs \
   curl 
  


  # download URL for the version 2.18 of the Illumina software
# http://support.illumina.com/content/dam/illumina-support/documents/downloads/software/bcl2fastq/bcl2fastq2-v2-18-0-12-linux-x86-64.zip
ADD http://support.illumina.com/content/dam/illumina-support/documents/downloads/software/bcl2fastq/bcl2fastq2-v2-18-0-12-linux-x86-64.zip /root/bcl2fastq2-v2-18-0-12-linux-x86-64.zip
RUN  (cd /root ; unzip /root/bcl2fastq2-v2-18-0-12-linux-x86-64.zip )
RUN rpm -i /root/bcl2fastq2-v2.18.0.12-Linux-x86_64.rpm 


# install CWL runner
# WILL STILL FAIL DUE TO OLD SETUPTOOLS to be fixed later
# RUN pip install cwlref-runner

