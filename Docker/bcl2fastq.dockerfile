# Use the latest CentOS image

# Command to build the image for Intel architecture on an M1 Mac
# docker buildx create --use
# docker buildx build --platform linux/amd64 -t bcl2fastq:latest .

# Command to run the container
# docker run -it --rm bcl2fastq:latest

FROM centos:latest

RUN sed -i s/mirror.centos.org/vault.centos.org/g /etc/yum.repos.d/CentOS-*.repo
RUN sed -i s/^#.*baseurl=http/baseurl=http/g /etc/yum.repos.d/CentOS-*.repo
RUN sed -i s/^mirrorlist=http/#mirrorlist=http/g /etc/yum.repos.d/CentOS-*.repo

# Install necessary dependencies
RUN yum update -y
RUN yum install -y epel-release
RUN yum install -y wget bzip2

# Download and install bcl2fastq
WORKDIR /tmp
COPY ./packages/bcl2fastq2-v2.20.0.422-Linux-x86_64.rpm .
# RUN wget http://support.illumina.com/content/dam/illumina-support/documents/downloads/software/bcl2fastq/bcl2fastq2-v2.20.0.422-Linux-x86_64.rpm
RUN yum localinstall -y bcl2fastq2-v2.20.0.422-Linux-x86_64.rpm
RUN rm -f bcl2fastq2-v2.20.0.422-Linux-x86_64.rpm

# Set the entrypoint
ENTRYPOINT ["bcl2fastq"]

