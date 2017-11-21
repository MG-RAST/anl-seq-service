#!/bin/bash

# redirection script
# install in /usr/local/bin and rename appropriatel
me=`basename "$0"`

/usr/local/share/anl-seq-service/bin/${me} ${@}
