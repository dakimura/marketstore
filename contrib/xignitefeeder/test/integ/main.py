#!/usr/bin/env python
# -*- coding:utf-8 -*-

import json
import datetime
import requests
import pymarketstore as pymkts

MSTORE_ENDPOINT = "http://localhost:5993/rpc"
MSTORE_STATS_ENDPOINT = "http://localhost:5993"


def get_memory_usage():
    # debug mode returns a text output
    res = requests.get(MSTORE_STATS_ENDPOINT + "/pprof/heap?debug=1")
    # scrape the
    alloc = res.content.split("# Alloc = ")[1].split("\n")[0]
    return int(alloc)


def get_num_goroutine():
    # debug mode returns a text output
    res = requests.get(MSTORE_STATS_ENDPOINT + "/pprof/goroutine?debug=1")
    # scrape the number of goroutines from the output
    num_goroutine = res.content.split("goroutine profile: total ")[1].split("\n")[0]
    return int(num_goroutine)


def get_delay(symbol, timeframe, attrgroup):
    client = pymkts.Client(MSTORE_ENDPOINT)

    now = datetime.datetime.utcnow()
    before3hours = now - datetime.timedelta(hours=300)
    start = "{0:%Y-%m-%d %H:%M:%S}".format(before3hours)

    param = pymkts.Params(symbol, timeframe, attrgroup, start=start)

    res = client.query(params=param)

    # get the time of the latest deal
    last_row = res.first().df()[-1:]
    last_deal_datetime = last_row.index[0].tz_convert(None)

    # return the delay
    return (now - last_deal_datetime).total_seconds()


def print_log(memory_usage, num_goroutine, toyota_delay):
    """
    print a log in stdout
    :param memory_usage: memory usage [Byte] of the marketstore with xignitefeeder
    :param num_goroutine: the number of go-routines in the marketstore instance
    :param toyota_delay: time lag difference between the following 2 times:
    1. current time
    2. time of the latest deal of Toyota in marketstore.
    Because Toyota is one of the most popular stocks and it has deals every second,
    this time can be used to check the delay of xignitefeeder
    :return:
    """
    current_time = datetime.datetime.utcnow().isoformat()
    log_obj = {
        "time": current_time,
        "memory_in_byte": memory_usage,
        "num_goroutine": num_goroutine,
        "toyota_delay_in_sec": toyota_delay
    }

    print(json.dumps(log_obj))


if __name__ == "__main__":
    # --- params ---
    symbol = '7203'  # TOYOTA
    timeframe = '1Sec'
    attrgroup = 'TICK'

    # --- get data ---
    alloc = get_memory_usage()
    num_goroutine = get_num_goroutine()
    delay = get_delay(symbol, timeframe, attrgroup)

    # --- output log ---
    print_log(alloc, num_goroutine, delay)
