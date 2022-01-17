FROM python:3

RUN apt-get update
RUN apt-get install -y \
    less \
    cmake \
    samtools \
    autotools-dev

# Pandas + numpy
RUN pip install pandas numpy cvxpy matplotlib

WORKDIR /usr/src/Build
RUN git clone https://github.com/andersen-lab/Freyja.git ;\
    git clone https://github.com/yatisht/usher.git ;\
    git clone https://github.com/andersen-lab/ivar.git ;

WORKDIR /usr/src/Build/kentsource
RUN wget http://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/faSomeRecords ;\
    wget http://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/faSize ; \
    chmod 775 *

# Usher

ENV APT_KEY_DONT_WARN_ON_DANGEROUS_USAGE=DontWarn
ENV DEBIAN_FRONTEND=noninteractive
USER root
RUN apt-get update && apt-get install -yq --no-install-recommends \
    git wget \
    ca-certificates \
    sudo python3
# WORKDIR /usr/src/Build/kentsource
# RUN wget http://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/faSomeRecords ;\
#     wget http://hgdownload.soe.ucsc.edu/admin/exe/linux.x86_64/faSize ;\
#     chmod 775 *
# WORKDIR /usr/src/Build/
# RUN git clone https://github.com/yatisht/usher.git 
WORKDIR /usr/src/Build/usher
RUN ./install/installUbuntu.sh 
ENV PATH=$PATH:/usr/src/Build/usher/build
# iVar
WORKDIR /usr/src/Build/
RUN wget https://github.com/samtools/htslib/releases/download/1.14/htslib-1.14.tar.bz2 ; \
    bzip2 -d htslib-1.14.tar.bz2 ; \
    tar -xf htslib-1.14.tar ; \
    cd htslib-1.14 ; \
    autoreconf -i  ; \
    ./configure ;\
    make ;\
    make install

# RUN git clone https://github.com/andersen-lab/ivar.git
# RUN cd ivar
WORKDIR /usr/src/Build/ivar
RUN ./autogen.sh ;\
    ./configure ;\
    make ;\
    make install


# Fryja
WORKDIR /usr/src/Build/Freyja
RUN make install 
RUN freyja update