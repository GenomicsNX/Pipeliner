#!/bin/bash

#. /usr/local/Modules/default/init/bash
module load python/3.5
module load graphviz

pipehome=$(dirname $0)
cd  $pipehome && python pipeliner2.py &
