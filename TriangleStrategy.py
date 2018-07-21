import FCoinRestLib
import time
import json
import datetime

class TriangleStrategy(object):
    # minimum trading volumn for the reference coin
    # BTC: 0.001; ETH: 0.01; USDT: price FT*15
    minNotional = 0.001

    # standard volumn used for triangle strategy
    buy_volumn = minNotional * 1.2

    # minimum trading volumn unit for the symbol|ref_coin[0], symbol|ref_coin[1] and ref_coin[1]|ref_coin[0]
    # for the trading group FT/USDT, FT/BTC, BTC/USDT
    minQty = [5, 5, 0.001]

    # minPrice = [0.000001, 0.0001, 0.000001]
    # price_precise = [int(-math.log10(x)) for x in minPrice]

    # volumn toloranz (0.05%) to match the request delay, that some one has already buy/sell with the detected price
    volumn_toloranz = 1.1

    # define trigger interval for trading
    trigger_threshold = 1.002
    def __init__(self, symbol, coin):
        self.symbol = symbol
        self.coin = coin
        self.price = {}

        # Use traiding minQty to ask first price, so that the requried buy/sell volumn can be estimated
        self.volumn = []
        for i in range(3):
            self.volumn.append({'buy':self.minQty[i],'sell':self.minQty[i]})

    def getTrianglePrice(self):   
        # Create 3 threads to get the 3 prices of triangle trading parallel
        thread1 = FCoinRestLib.getPriceThread(1, "Thread-1", self.symbol, self.coin[0], self.volumn[0])
        thread2 = FCoinRestLib.getPriceThread(2, "Thread-2", self.symbol, self.coin[1], self.volumn[1])
        thread3 = FCoinRestLib.getPriceThread(3, "Thread-3", self.coin[1], self.coin[0], self.volumn[2])

        # Start new Threads
        thread1.start()
        thread2.start()
        thread3.start()

        # Wait for all threads to complete
        thread1.join()
        thread2.join()
        thread3.join()

        # Get the price from thread back and calculate the triangle price
        self.price['direct_buy'] = thread1.price['asks_vol']
        self.price['direct_sell'] = thread1.price['bids_vol']
        # Add sell_1 price for limit trading
        self.price['direct_sell_1'] = thread1.price['bids_1']

        self.price['between_buy'] = thread2.price['asks_vol']
        self.price['between_sell'] = thread2.price['bids_vol']
        # Add buy_1 price for limit between sell
        self.price['between_buy_1'] = thread2.price['asks_1']

        self.price['rate_buy'] = thread3.price['asks_vol']
        self.price['rate_sell'] = thread3.price['bids_vol']
        # Add buy_1 price for limit rate sell
        self.price['rate_buy_1'] = thread3.price['asks_1']

        # Two trading directions are possible:
        # 1. coin[0] --> coin[1](between) --> symbol --> coin[0]: call BBS (buy buy sell)
        # 2. coin[0] --> symbol --> coin[1](between) --> coin[0]: call BSS (buy sell sell)
        # Calculate BBS price and win
        self.price['BBS_price'] = self.price['between_buy']*self.price['rate_buy'] 
        self.price['BBS_win'] = self.price['direct_sell']/self.price['BBS_price']
        # Calculate BSS price and win
        self.price['BSS_price'] = self.price['between_sell']*self.price['rate_sell'] 
        self.price['BSS_win'] = self.price['BSS_price']/self.price['direct_buy']

        #TODO Test Code
        # self.price['BBS_win'] = self.price['BSS_price']/self.price['direct_buy']
        # self.price['BSS_win'] = self.price['BSS_price']/(self.price['direct_sell']+0.00001)

        # Prepare the volumn for the next price request
        # calculate symbol buy volumn with min quantity of between coin (BTC, ETH)
        symoble_buy = self.buy_volumn/self.price['between_buy']
        symbole_sell =  self.buy_volumn/self.price['between_sell']

        # Direct trading volumn
        self.volumn[0]['buy'] = symoble_buy*self.volumn_toloranz
        self.volumn[0]['sell'] = symbole_sell*self.volumn_toloranz

        # Between trading volumn
        self.volumn[1]['buy'] = symoble_buy*self.volumn_toloranz
        self.volumn[1]['sell'] = symoble_buy*self.volumn_toloranz

        # Rate trading volumn
        self.volumn[2]['buy'] = self.buy_volumn*self.volumn_toloranz
        self.volumn[2]['sell'] = self.buy_volumn*self.volumn_toloranz

        print("Price: --------")
        print(self.price)
        print("Volumn: --------")
        print(self.volumn)


# possible triangle trading combination
ref_coin = [['usdt', 'btc'], ['usdt','eth']]

test = TriangleStrategy('ft',ref_coin[0])

while True:
    test.getTrianglePrice()
    # if test.price['BSS_win'] > 1:

    between_limit_sell = test.price['between_buy_1']
    limit_win = between_limit_sell*test.price['rate_sell']/test.price['direct_buy']
    if limit_win > 1.0001:
        fout = open("TradingRecord",'a')
        fout.write(str(datetime.datetime.now()))
        # json.dump(test.price,fout)
        fout.write("    ")
        fout.write(limit_win)
        fout.write("\n")
        fout.close()

        print("Find out a trading chance!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print(limit_win)
    time.sleep(2)