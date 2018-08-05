import FCoinRestLib
import time
import datetime
import json
import fcoin3
import math


class TriangleStrategy(object):
    # minimum trading volumn for the reference coin
    # BTC: 0.001; ETH: 0.01; USDT: 6.23
    minNotional = 0.001

    # standard volumn used for triangle strategy
    # buy_volumn = minNotional * 1

    # minimum trading volumn unit for the symbol|ref_coin[0], symbol|ref_coin[1] and ref_coin[1]|ref_coin[0]
    # for the trading group FT/USDT, FT/BTC, BTC/USDT
    # minQty = [0.0001, 0.0001, 0.000001]

    # minPrice = [0.000001, 0.0001, 0.000001]
    # price_precise = [int(-math.log10(x)) for x in minPrice]

    # volumn toloranz (0.05%) to match the request delay, that some one has already buy/sell with the detected price
    volumn_toloranz = 1.1

    # define trigger interval for trading
    trigger_threshold = 1.003

    # target win rate
    target_win_rate = 0.0006

    # Fee quote, which is use to calculate exactly selling volumn
    fee_quote = 0.001

    def __init__(self, symbol, coin):
        self.fcoin = fcoin3.Fcoin()
        self.fcoin.auth(FCoinRestLib.APIKey, FCoinRestLib.privateKey)

        self.symbol = symbol
        self.coin = coin
        self.price = {}

        self.getExchangeInfo()

        # Use traiding minQty to ask first price, so that the requried buy/sell volumn can be estimated
        self.volumn = []
        for i in range(3):
            self.volumn.append({'buy':self.minQty[i],'sell':self.minQty[i]})

        self.balance_coin_list = coin
        self.balance_coin_list.append(symbol)
        self.saveAccountInfo()

    def saveAccountInfo(self):
        # get the current price
        self.getTrianglePrice()

        file_out = open('AccountInfo.log','a')
        # save date time
        file_out.write(str(datetime.datetime.now())+'\n')
        file_out.write(str(time.time())+'\n')

        # get balance
        balance = FCoinRestLib.getBalance(self.balance_coin_list)
        json.dump(balance, file_out)
        file_out.write("\n")

        # calculate the total price in coin 0 (usdt)
        symbol_free = float(balance[self.symbol])*self.price['direct_sell']
        between_free = float(balance[self.coin[1]])*self.price['rate_sell']
        total_free = float(balance[self.coin[0]]) + symbol_free + between_free
        file_out.write("Total balance in " + str(self.coin[0]) + " is: ")
        file_out.write(str(total_free))

        file_out.write('\n\n')
        file_out.close()

    def getExchangeInfo(self):
        exchangeInfo = self.fcoin.get_symbols()

        # minimum trading price unit for the symbol|ref_coin[0], symbol|ref_coin[1] and ref_coin[1]|ref_coin[0]
        self.minPrice = []
        self.price_precise = []
        self.minQty = []

        # get exchange info from symbol|ref_coin[0]
        # get all filters for the target trading symbol
        filters = next(item for item in exchangeInfo if item['name'] == str(self.symbol+self.coin[0]))['price_decimal']
        self.price_precise.append(filters)
        Qty = next(item for item in exchangeInfo if item['name'] == str(self.symbol+self.coin[0]))['amount_decimal']
        self.minQty.append(10**(-1*Qty))

        # get exchange info from symbol|ref_coin[1]
        filters = next(item for item in exchangeInfo if item['name'] == str(self.symbol+self.coin[1]))['price_decimal']
        self.price_precise.append(filters)
        Qty = next(item for item in exchangeInfo if item['name'] == str(self.symbol+self.coin[1]))['amount_decimal']
        self.minQty.append(10**(-1*Qty))

        # get exchange info from ref_coin[1]|ref_coin[0]
        filters = next(item for item in exchangeInfo if item['name'] == str(self.coin[1]+self.coin[0]))['price_decimal']
        self.price_precise.append(filters)
        Qty = next(item for item in exchangeInfo if item['name'] == str(self.coin[1]+self.coin[0]))['amount_decimal']
        self.minQty.append(10**(-1*Qty))

        # calculate the precise
        self.minPrice = [math.pow(10,-x) for x in self.price_precise]

        print(self.minPrice)
        print(self.price_precise)
        print(self.minQty)

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

        # calculate buy volumn based on the BTC minNotation
        self.buy_volumn = self.minNotional*self.price['rate_buy']
        print("Current buy Volumn is: ", self.buy_volumn)

        # Prepare the volumn for the next price request
        symoble_buy = self.buy_volumn/self.price['direct_buy']
        symbole_sell =  self.buy_volumn/self.price['direct_sell']
        
        # Direct trading volumn
        self.volumn[0]['buy'] = symoble_buy*self.volumn_toloranz
        self.volumn[0]['sell'] = symbole_sell*self.volumn_toloranz

        # Between trading volumn
        self.volumn[1]['buy'] = symoble_buy*self.price['between_buy']*self.volumn_toloranz
        self.volumn[1]['sell'] = symoble_buy*self.price['between_sell']*self.volumn_toloranz

        # Rate trading volumn
        self.volumn[2]['buy'] = (self.buy_volumn/self.price['rate_buy'])*self.volumn_toloranz
        self.volumn[2]['sell'] = (self.buy_volumn/self.price['rate_sell'])*self.volumn_toloranz

        print("Price: --------")
        print(self.price)
        print("Volumn: --------")
        print(self.volumn)


    # Use limit Direct Buy and also limit sell of between coin
    def triangleTradingLimitTwice(self):
        # recalculate the direct buy price with sell price (bid_1) + minPrice allowed by platform
        self.price['direct_buy'] = round(float(self.price['direct_sell_1'] + self.minPrice[0]),self.price_precise[0])
        # recalculate the between sell price with buy price (ask_1) - minPrice allowed by platform
        self.price['between_sell'] = round(float(self.price['between_buy_1'] - self.minPrice[1]*3),self.price_precise[1])
        # Calculate BSS price and win
        self.price['BSS_price'] = self.price['between_sell']*self.price['rate_sell'] 
        self.price['BSS_win'] = self.price['BSS_price']/self.price['direct_buy']

        # print(self.price, " @", self.price_time)

        # in case the BSS minuse handling fee (0.15%) is still cheeper
        if self.price['BSS_win'] > self.trigger_threshold:
            self.trading_begin_time = int(time.time()*1000)

            # because of the minimum quantity of the trading, calculate how much target Coin(symbol) should be buy with triangle price
            self.cal_buy_volumn_symbol = self.buy_volumn/self.price['direct_buy']
            # self.real_buy_volumn_symbol = (int(self.cal_buy_volumn_symbol/self.minQty[0]))*self.minQty[0]
            buy_volumn_precise = int(-math.log10(self.minQty[0]))
            self.real_buy_volumn_symbol = round(self.cal_buy_volumn_symbol,buy_volumn_precise)
            

            # becasue the fee is withdrewed directly from trading volumn, calculate the sell volumn from target coin
            self.cal_sell_volumn_symbol = self.real_buy_volumn_symbol*(1-self.fee_quote)
            self.real_sell_volumn_symbol = (int(self.cal_sell_volumn_symbol/self.minQty[1]))*self.minQty[1]
            self.real_sell_volumn_symbol = round(self.real_sell_volumn_symbol, buy_volumn_precise)

            # caclulate how much between reference coin is needed based on real selling volumn
            # because in FCoin, the market selling price is based on coin0 (usdt), use the bss price to calculate the volumn
            self.cal_trading_volumn_between = self.real_sell_volumn_symbol*self.price['between_sell']*(1-self.fee_quote)

            # use round up integer to calculate the needed between reference coin volumn
            # self.real_trading_volumn_between = (math.ceil(self.cal_trading_volumn_between/self.minQty[2]))*self.minQty[2]
            # use round instead of ceil to balance the volumn of Between Coin and Main Coin
            between_volumn_precise = int(-math.log10(self.minQty[2]))
            self.real_trading_volumn_between = round(self.cal_trading_volumn_between,between_volumn_precise)
            
            # buy target coin with direct reference coin in Limit Trading
            # self.response_1 = BinanceRestLib.createLimitOrder(self.symbol,self.coin[0],"BUY",self.real_buy_volumn_symbol,self.price['direct_buy'],self.time_offset)
            self.response_1 = self.fcoin.buy(self.symbol+self.coin[0], self.price['direct_buy'], self.real_buy_volumn_symbol)

            print("Fill the triangle trading condition ----------------------------------")
            print("Calculated Buy Symbol: ", self.cal_buy_volumn_symbol)
            print("Real Buy Symbol: ", self.real_buy_volumn_symbol)
            print("Calculated Sell Symbol: ", self.cal_sell_volumn_symbol)
            print("Real Sell Symbol: ", self.real_sell_volumn_symbol)
            print("Calculated Trading Between: ", self.cal_trading_volumn_between)
            print("Real Trading Between: ",self.real_trading_volumn_between)

            print("Response_1------------------------")
            print(json.dumps(self.response_1, indent=4))
            
            # get the order id
            orderId = self.response_1['data']
            
            # wait a small time interval, until the limit trad is taken by the others
            for i in range(2):
                self.limit_order = self.fcoin.get_order(orderId)
                if 'data' in self.limit_order:
                    self.limit_order = self.limit_order['data']
                    # if the order is filled, complete the triangle trading
                    if self.limit_order['state'] == "filled":
                        # finish the selling process
                        self.triangleTradingSellLimit()
                        
                        return 1
                else:
                    print("Unknown response:")
                    print(json.dumps(self.limit_order, indent=4))

                print("End of %dth loop" %(i))

            # if the limit trading is not taken by others, cancel it
            self.cancel_limit_order = self.fcoin.cancel_order(orderId)
            print("cancel_limit_order------------------------")
            print(json.dumps(self.cancel_limit_order, indent=4))
            
            # some times the trading is already executed, in this case a error code will be returned
            # if 'msg' in self.cancel_limit_order:
            # No return, if a HttpError Exception has been catched in fcoin3 in Siagned Request
            if self.cancel_limit_order is None:
                print("Special Case: the trading is already filled. Complete the rest selling phase")
                # finish the selling process
                self.triangleTradingSellLimit()

                return 1
            
            # check whether some part of the trading is already completed before cancel
            # get the current price
            thread1 = FCoinRestLib.getPriceThread(1, "Thread-1", self.symbol, self.coin[0], self.volumn[0])
            thread1.start()

            self.cancel_order = self.fcoin.get_order(orderId)
            print("cancel_order------------------------")
            print(json.dumps(self.cancel_order, indent=4))

            thread1.join()

            # calculate the trading price
            cancel_sell_price = round(float(thread1.price['asks_1'] - self.minPrice[0]),self.price_precise[0])

            # if only a part is completed sell them directly
            # check whether the response is sucessfully
            if 'data' in self.cancel_order:
                self.cancel_order = self.cancel_order['data']
                # check whether the state is marked as "partial_canceled"
                if self.cancel_order['state'] == 'partial_canceled':
                    print("Sell the not canceled part")
                    # calculate already filled volumn
                    cal_cancel_volumn = float(self.cancel_order['filled_amount']) - float(self.cancel_order['fill_fees'])
                    real_cancel_volumn = (int(cal_cancel_volumn/self.minQty[0]))*self.minQty[0]

                    # create a limit trade to sell all target coin back to coin[0], with the sell_1 price
                    self.limit_order = self.fcoin.sell(self.symbol+self.coin[0], cancel_sell_price, real_cancel_volumn)
                    
                    limit_order_Id = self.limit_order['data']

                    # wait until the trading is completed
                    while True:
                        time.sleep(1)
                        # print("Waiting limit sell for target coin ...")
                        self.limit_order = self.fcoin.get_order(limit_order_Id)
                        if 'data' in self.limit_order:
                            self.limit_order = self.limit_order['data']
                            if self.limit_order['state'] == "filled":
                                break
                            # if the trading is cancelled manually, wait 5 min for the next rund
                            if self.limit_order['state'] == "canceled":
                                print("Cancel the trading and sell the coin manually")
                                time.sleep(300)
                                break
                        else:
                            print("Unknown status:")
                            print(json.dumps(self.limit_order, indent=4))
                      
                    print(json.dumps(self.limit_order, indent=4))  
                
                if self.cancel_order['state'] == 'filled' or self.cancel_order['state'] == 'pending_cancel':
                    print("Trade is canceled at the same time as the state is returned")
                    # finish the selling process
                    self.triangleTradingSellLimit()
                    return 1

        self.trading_end_time = int(time.time()*1000)
        return 0

    # the sell phase always with limit trading on between coin    
    def triangleTradingSellLimit(self):
        # get current between sell price
        thread2 = FCoinRestLib.getPriceThread(2, "Thread-2", self.symbol, self.coin[1], self.volumn[1])
        thread2.start()

        # sell between refrence coin with market price firstly
        self.response_3 = self.fcoin.sellMarket(self.coin[1]+self.coin[0], self.real_trading_volumn_between)
        print(json.dumps(self.response_3, indent=4))

        thread2.join()
        
        # # create a current sell price based on current sell_1 price
        # current_between_sell = round(float(thread2.price['asks_1'] - self.minPrice[1]),self.price_precise[1])
        # # calculate minimum price to sell the between coin without loss
        # #TODO: need to get the real selling price from response3
        # minimum_between_sell = round((self.price['direct_buy']*1.0015/self.price['rate_sell']),self.price_precise[1])

        # print(self.price, " @", self.price_time)
        # print("Saved price: ", self.price['between_sell'])
        # print("Current sell price: ", current_between_sell)
        # print("Minimum sell price: ", minimum_between_sell)
        
        # # choose the bigger price betwen current sell price and minimum sell price as the executing selling price
        # if minimum_between_sell > current_between_sell:
        #     self.price['between_sell'] = minimum_between_sell
        # else:
        #     self.price['between_sell'] = current_between_sell

        # use a conservative trading price to garantee the continue tradings
        minimum_between_sell = round((self.price['direct_buy']*(self.trigger_threshold+self.target_win_rate)/self.price['rate_sell']),self.price_precise[1])
        self.price['between_sell'] = minimum_between_sell
        print("Saved price: ", self.price['between_sell'])
        print("Minimum sell price: ", minimum_between_sell)

        print("begin between sell")

        # create limit trading for between coin
        self.response_2 = self.fcoin.sell(self.symbol+self.coin[1], self.price['between_sell'], self.real_sell_volumn_symbol)

        print(json.dumps(self.response_2, indent=4))

        # get the order id
        orderId = self.response_2['data']

        # check the order state
        self.limit_order = self.fcoin.get_order(orderId)

        begin_waiting_time = time.time()
        begin_time = time.time()
        # wait until the limit order is filled
        while True:
            time.sleep(1)
            # print("Waiting limit sell for bewteen coin ...")
            self.limit_order = self.fcoin.get_order(orderId)
            if 'data' in self.limit_order:
                self.limit_order = self.limit_order['data']
                if self.limit_order['state'] == "filled":
                    # update the basic buy volumn with last win
                    self.minNotional *= (1+self.target_win_rate)
                    print("New Basic Buy Volumn is: ", self.buy_volumn)
                    break
                # if the trading is cancelled manually, wait 5 min for the next rund
                if self.limit_order['state'] == "canceled":
                    print("Cancel the trading and sell the coin manually")
                    time.sleep(300)
                    break
            else:
                print("Unknown status:")
                print(json.dumps(self.limit_order, indent=4))

            # resnycho time offset in every 10min
            if time.time()-begin_time > 600:                
                # if the limit sell is already hold more than 3hours, just keep the current limit sell and restart a round once again.
                if time.time()-begin_waiting_time > 10800:
                    current_price = FCoinRestLib.getCurrentPrice(self.symbol, self.coin[1], self.volumn[1])
                    print("Special case, that a limit trade is not taken for a long time. ", current_price['asks_vol'])
                    # in case the current limit sell price is 5% less than the expected one
                    if current_price['asks_vol']/self.price['between_sell'] < 0.95:
                        break

        print(json.dumps(self.limit_order, indent=4))

        self.saveAccountInfo()
        
        self.trading_end_time = int(time.time()*1000)

    def writeLog(self):
        file_out = open('TradingInfo.log','a')
        file_out.write(str(datetime.datetime.now())+'\n')
        file_out.write(str(self.price) + '\n')

        file_out.write("Fill the triangle trading condition ----------------------------------")
        file_out.write("Calculated Buy Symbol: %f \n" %(self.cal_buy_volumn_symbol))
        file_out.write("Real Buy Symbol: %f \n" %(self.real_buy_volumn_symbol))
        file_out.write("Calculated Trading Between: %f \n"  %(self.cal_trading_volumn_between))
        file_out.write("Real Trading Between: %f \n" %(self.real_trading_volumn_between))

        file_out.write("Trading begin -------------------------------@ %f \n" %(self.trading_begin_time))
        file_out.write("Step 1:\n")
        json.dump(self.response_1, file_out)
        file_out.write("Step 2:\n")
        json.dump(self.response_2, file_out)
        file_out.write("Step 3:\n")
        json.dump(self.response_3, file_out)
        file_out.write("Trading end -------------------------------@ %f \n" %(self.trading_end_time))

        file_out.write("Buy volumn: %f \n" %(self.real_buy_volumn_symbol))
        file_out.write("Sell volumn: %f \n" %(self.real_sell_volumn_symbol))
        file_out.write("Between Sell volumn: %f \n" %(self.real_trading_volumn_between))

        file_out.close()

