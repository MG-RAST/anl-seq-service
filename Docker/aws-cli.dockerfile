FROM ubuntu:latest

RUN apt update -y && apt install -y \
    curl \
    less \
    python3 \
    unzip \
    vim

# RUN apt install -y \
#     glibc

RUN apt install -y groff


WORKDIR /build 
RUN curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip" 
RUN unzip awscliv2.zip
RUN ./aws/install

# Bind credential files to /aws/credentials
WORKDIR /aws
ENV AWS_SHARED_CREDENTIALS_FILE=/aws/credentials

# mount point for data dir
WORKDIR /data
ENTRYPOINT [ "aws" ]