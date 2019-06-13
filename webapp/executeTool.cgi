#!/bin/bash

echo "Content-Type: text/html"
echo ""



echo ""
#while read line
#do
#  echo "$line"
#done < "${1:-/dev/stdin}"

cd ..
pwd=`pwd`
PYTHONPATH=$pwd; export PYTHONPATH
export PYTHONIOENCODING=utf8
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export LANGUAGE=en_US.UTF-8
DFP_YAML_TEMPLATE="$pwd/googleads_cgi.yaml"; export DFP_YAML_TEMPLATE

#echo "running..."

source ../python_dfp/bin/activate
cd /tmp
python "$pwd/webapp/cgiHandler.py" 2>&1