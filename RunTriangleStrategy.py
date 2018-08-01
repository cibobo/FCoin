import TriangleStrategy
import time

# possible triangle trading combination
ref_coin = [['usdt', 'btc'], ['usdt','eth']]

trading_times = 0
max_tradings = 5

test = TriangleStrategy.TriangleStrategy('ft',ref_coin[0])

while True:
    # test.getTrianglePrice()
    # if test.price['BSS_win'] > 1:

    # between_limit_sell = test.price['between_buy_1']
    # limit_win = between_limit_sell*test.price['rate_sell']/test.price['direct_buy']
    # if limit_win > 1.003:
    #     print("Find out a trading chance!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
    #     print(limit_win)
    # time.sleep(2)


    test.getTrianglePrice()
    result = test.triangleTradingLimitTwice()
    # if one trading is compelted
    if result == 1:
        print("Trading ", trading_times, " is completed --------------------------------------")
        test.writeLog()
        trading_times += 1
        if trading_times > max_tradings:
            break

    time.sleep(1)