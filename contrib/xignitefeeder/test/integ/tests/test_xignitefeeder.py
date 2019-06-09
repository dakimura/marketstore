# -*- coding:utf-8 -*-


import pymarketstore as pymkts

MARKETSTORE_ENDPOINT = "http://localhost:5993/rpc"


#
# def test_init():
#     p = pymkts.Params('TSLA', '1Min', 'OHLCV', 1500000000, 4294967296)
#     tbk = "TSLA/1Min/OHLCV"
#     assert p.tbk == tbk
#

def test_client_init():
    c = pymkts.Client(MARKETSTORE_ENDPOINT)

    symbol = '1301'
    timeframe = '1D'
    attrgroup = 'OHLCV'
    param = pymkts.Params(symbol, timeframe, attrgroup, start='1970-01-01 00:00:00')
    query_reply = c.query(params=param)

    print(query_reply.first().df())
    # assert isinstance(c.rpc, pymkts.client.MsgpackRpcClient)

def test_list_symbols():
    # --- given ---
    timeframe = '1Sec'
    attrgroup = 'TICK'

    c = pymkts.Client(MARKETSTORE_ENDPOINT)

    # --- when ---
    counter = 0

    reply = c.list_symbols()
    print(len(reply))

    # --- then ---


def test_realtime_data():
    # --- given ---
    timeframe = '1Sec'
    attrgroup = 'TICK'

    c = pymkts.Client(MARKETSTORE_ENDPOINT)
    symbols = get_realtime_stocks()
    symbols.sort()

    # --- when ---
    counter = 0
    for symbol in symbols:
        counter += 1
        param = pymkts.Params(symbol, timeframe, attrgroup, start='2019-06-07 09:00:00')
        reply = c.query(params=param)

        # --- then ---
        print("[symbol]" + str(symbol))
        columns = reply.results[0].first().df().columns
        assert all([a == b for a, b in zip(columns, ['Ask', 'Bid', 'Last'])])

        if counter == 100:
            return
        # テスト終わったらmemori, goroutine数、トヨタの遅延チェック用のcron作成

def test_historical_data():
    # --- given ---
    timeframe = '1D'
    attrgroup = 'OHLCV'

    c = pymkts.Client(MARKETSTORE_ENDPOINT)
    # symbols = c.list_symbols()
    symbols = get_historical_stocks()
    symbols.sort()

    # --- when ---
    for symbol in symbols:
        param = pymkts.Params(symbol, timeframe, attrgroup, start='2019-06-03 00:00:00')
        reply = c.query(params=param)

        # --- then ---
        print("[symbol]" + str(symbol))
        print(reply.first().df())


def get_historical_stocks():
    historical_stocks = []
    with open("historical_stocks_20190606.txt", "r") as f:
        for line in f:
            historical_stocks.append(line.rstrip())

    return historical_stocks


def get_realtime_stocks():
    realtime_stocks = []
    with open("realtime_stocks_20190607.txt", "r") as f:
        for line in f:
            realtime_stocks.append(line.rstrip())

    return realtime_stocks

# def test_real_time_last():
#     c = pymkts.Client(MARKETSTORE_ENDPOINT)
#
#     symbol = '1301'
#     timeframe = '1D'
#     attrgroup = 'OHLCV'
#
#     reply = c.list_symbols()
#     print(reply)
#     もうmarketstoreにbackfillは入ってるからそれでテストかけ
