import fcoin3
import json
import threading

APIKey = '8d713ea46bfb94f874f689'
privateKey = '787a73f4cab953dd41c87e'


class getPriceThread (threading.Thread):
   def __init__(self, threadID, name, symbol, coin, volumn):
      threading.Thread.__init__(self)
      self.threadID = threadID
      self.name = name
      self.symbol = symbol
      self.coin = coin
      self.volumn = volumn
      self.price = {}
   def run(self):
    #   print('Start thread of ' + self.name + '@' + str(time.time()))
      self.price = getCurrentPrice(self.symbol, self.coin, self.volumn)
    #   print("Price of %s and %s is %f" %(self.symbol, self.coin, self.price))
    #   print('End thred of ' + self.name + '@' + str(time.time()))


def getCurrentPrice(symbol, ref_coin, volumn):
    # conbine the trading symbol
    symbol = symbol + ref_coin
    
    fcoin = fcoin3.Fcoin()
    # call rest api to get the current depth data. Using L20 firstly
    depth_level = 20
    result = fcoin.get_market_depth('L'+str(depth_level), symbol)
    depth = result['data']

    price = {}
    # consider also the required volumn
    remain_buy_volumn = volumn['buy']
    remain_sell_volumn = volumn['sell']
    temp_buy_price = 0
    temp_sell_price = 0

    for i in range(depth_level):
        temp = remain_buy_volumn - float(depth['asks'][2*i+1])
        # if the current price can't cover the remain volumn
        if temp>0:
            # consider also the next order
            temp_buy_price += float(depth['asks'][2*i+1])*float(depth['asks'][2*i])
            remain_buy_volumn = temp
            # print("Sepecial case! buy volumn remaining for %s is %f" %(symbol+ref_coin,remain_buy_volumn))
            # print(depth)
        else:
            temp_buy_price += remain_buy_volumn*float(depth['asks'][2*i])
            remain_buy_volumn = temp
            break
    if remain_buy_volumn<=0:
        price['asks_vol'] = round(temp_buy_price/volumn['buy'],8)
    else:
        price['asks_vol'] = 'NAN'

    for i in range(depth_level):
        temp = remain_sell_volumn - float(depth['bids'][2*i+1])
        # if the current price can't cover the remain volumn
        if temp>0:
            temp_sell_price += float(depth['bids'][2*i+1])*float(depth['bids'][2*i])
            remain_sell_volumn = temp
            # print("Sepecial case! sell volumn remaining for %s is %f" %(symbol+ref_coin,remain_sell_volumn))
            # print(depth)
        else:
            temp_sell_price += remain_sell_volumn*float(depth['bids'][2*i])
            remain_sell_volumn = temp
            break
    if remain_sell_volumn<=0:
        price['bids_vol'] = round(temp_sell_price/volumn['sell'],8)
    else:
        price['bids_vol'] = 'NAN'

    # TODO 2: consider also the second/third price
    # price['sell'] = float(depth['bids'][0][0])
    # price['buy'] = float(depth['asks'][0][0])

    # return also the sell_1 (bids_1) price
    price['bids_1'] = float(depth['bids'][0])
    # return also the buy_1 (asks_1) price
    price['asks_1'] = float(depth['asks'][0])

    return price

def getBalance(coin_list):
    fcoin = fcoin3.Fcoin()

    fcoin.key = APIKey
    fcoin.secret = privateKey.encode('UTF-8')

    response = fcoin.get_balance()
    balance = response['data']
    # loop for all required coins, find the balance and save them
    free = {}
    for coin in coin_list:
        # use generator expression to find out the key value from a list in dictionary
        free[coin] = next(item for item in balance if item['currency']==coin)['available']
    return free