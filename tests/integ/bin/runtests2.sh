#!/bin/bash

rm -rf testdata test_ticks.csv && mkdir -p testdata/mktsdb
if [ $? -ne 0 ]; then \
    echo "Failed: cannot delete testdata and/or make testdata/mktsdb directory"
    exit 1;
fi


# import ticks-example-1.csv/yaml to TEST/1Min/TICK and check if the output of show commands match ticks-example-1-output.csv
marketstore connect -d `pwd`/testdata/mktsdb <<- EOF
\create TEST/1Min/TICK:Symbol/Timeframe/AttributeGroup Bid,Ask/float32 variable
\getinfo TEST/1Min/TICK
\load TEST/1Min/TICK bin/ticks-example-not-sorted-by-time.csv bin/ticks-example-not-sorted-by-time.yaml
\o test_ticks.csv
\show TEST/1Min/TICK 1970-01-01
EOF
if [ $? -ne 0 ]; then exit 1; fi

diff -q bin/ticks-example-not-sorted-by-time-output.csv test_ticks.csv && echo "Passed"
if [ $? -ne 0 ];
then
    echo "Failed"
    exit 1;
fi

rm -f test_ticks.csv
if [ $? -ne 0 ];
then
    echo "Failed"
    exit 1;
fi


# remove the temporary files
rm -rf testdata test_ticks.csv tmp.csv
