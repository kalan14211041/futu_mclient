from futu import *
import os, math

# Reference:
#   https://openapi.futunn.com/futu-api-doc/quick/strategy-sample.html
#   https://openapi.futunn.com/futu-api-doc/trade/overview.html

############################ CONFIG ############################
FUTUOPEND_ADDR = '127.0.0.1'
FUTUOPEND_PORT = 11111

TRADING_ENVIRONMENT = TrdEnv.REAL # TrdEnv.SIMULATE
TRADING_MARKET = TrdMarket.HK

quote_context = OpenQuoteContext(host=FUTUOPEND_ADDR, port=FUTUOPEND_PORT)
trade_context = OpenSecTradeContext(filter_trdmarket=TRADING_MARKET, host=FUTUOPEND_ADDR, port=FUTUOPEND_PORT, security_firm=SecurityFirm.FUTUSECURITIES)

def _print_data_table(data):
    print(data)
    for key in data:
        col = data[key].values.tolist()
        if col == ['N/A'] or col == [0.0] or data[key].isnull().values.all():
            continue
        print("\t", key, col)

######## Accounts ########

def list_accounts():
    ret, data = trade_context.get_acc_list()
    if ret == RET_OK:
        print("<-- Account list")
        _print_data_table(data)
        print(data['acc_id'].values.tolist())
        # First accout should be REAL trade account
        return data['acc_id'].values.tolist()
    else:
        print('<-- get_acc_list error: ', data)
        return None

def unlock_trade():
    pswd = os.getenv('FUTU_TRADING_PSWD')
    if pswd == None:
        print('No FUTU_TRADING_PSWD set in ENV')
        return False
    if TRADING_ENVIRONMENT == TrdEnv.REAL:
        ret, data = trade_context.unlock_trade(pswd)
        if ret != RET_OK:
            print('<-- failed in unlock_trade()', data)
            return False
        print("<-- Trade unlocked")
    return True

def account_info():
    ret, data = trade_context.accinfo_query()
    if ret == RET_OK:
        print("<-- Account info")
        _print_data_table(data)
        return data
    else:
        print('<-- accinfo_query error: ', data)
        return None

def list_position():
    ret, data = trade_context.position_list_query()
    if ret == RET_OK:
        print("<-- Position list")
        _print_data_table(data)
        return data
    else:
        print('<-- position_list_query error: ', data)
        return None

######## Trading & Rules ########

def price_step(code):
    open_quantity = 0
    ret, data = quote_context.get_market_snapshot([code])
    if ret != RET_OK:
        print('<-- Failed in getting market snapshot', data)
    print('<-- Trading rule & market snapshot', code)
    _print_data_table(data)
    qty_step = data['lot_size'][0]
    price_step = data['price_spread'][0]
    print("<--", code, 'qty', qty_step, 'price_step', price_step)
    return qty_step, price_step

######## Untest below ########

def get_holding_position(code):
    holding_position = 0
    ret, data = trade_context.position_list_query(code=code, trd_env=TRADING_ENVIRONMENT)
    if ret != RET_OK:
        print('Failed in getting position', code, data)
        return None
    else:
        if data.shape[0] > 0:
            holding_position = data['qty'][0]
        print('Position {} {}'.format(code, holding_position))
    return holding_position

def get_ask_and_bid(code):
    ret, data = quote_context.get_order_book(code, num=1)
    if ret != RET_OK:
        print('No L1 for ', code, data)
        return None, None
    return data['Ask'][0][0], data['Bid'][0][0]

def is_valid_quantity(code, quantity, price):
    ret, data = trade_context.acctradinginfo_query(
            order_type=OrderType.NORMAL, code=code, price=price,
            trd_env=TRADING_ENVIRONMENT)
    if ret != RET_OK:
        print('Failed in getting valid qty', code, data)
        return False
    max_can_buy = data['max_cash_buy'][0]
    max_can_sell = data['max_position_sell'][0]
    if quantity > 0:
        return quantity < max_can_buy
    elif quantity < 0:
        return abs(quantity) < max_can_sell
    return false

def show_order_status(data):
    order_status = data['order_status'][0]
    order_info = dict()
    order_info['code'] = data['code'][0]
    order_info['price'] = data['price'][0]
    order_info['side'] = data['trd_side'][0]
    order_info['qty'] = data['qty'][0]
    print('status', order_status, order_info)

def test_buy_trade(code):
    ask, bid = get_ask_and_bid(code)
    open_quantity = 100
    if is_valid_quantity(code, open_quantity, ask) == False:
        print('Order quantity beyond valid amount.')
        return None
    ret, data = trade_context.place_order(
            price=ask, qty=open_quantity, code=code, trd_side=TrdSide.BUY,
            order_type=OrderType.NORMAL, trd_env=TRADING_ENVIRONMENT,
            remark='moving_average_strategy')
    if ret != RET_OK:
        print('Failed in placing order', data)

def test_sell_9618():
    print('Start selling 9618')
    # SELL HK.09618
    TARGET_STOCK = 'HK.09618'
    while True:
        refresh_cache = False
        time.sleep(3 if refresh_cache else 1)
        ret, data = trade_context.position_list_query(code=TARGET_STOCK, refresh_cache=refresh_cache)
        if ret == RET_OK:
            position_cache = data
            if position_cache.shape[0] > 0:
                if position_cache['code'][0] == TARGET_STOCK:
                    can_sell_qty = position_cache['can_sell_qty'][0]
                    if can_sell_qty > 50:
                        close_quantity = int(can_sell_qty/50) * 50
                        ask, bid = get_ask_and_bid(TARGET_STOCK)
                        if is_valid_quantity(TARGET_STOCK, -close_quantity, bid):
                            ret, data = trade_context.place_order(price=bid, qty=quantity, code=TARGET_STOCK, trd_side=TrdSide.SELL,
                                    order_type=OrderType.NORMAL, trd_env=TRADING_ENVIRONMENT, remark=f'Sell {close_quantity}')
                            if ret != RET_OK:
                                print('平仓失败：', data)

############################ Callbacks ############################
def on_init():
    if not unlock_trade():
        return False
    print('************ ON_INIT ***********')
    return True

EXAMPLE_CODE = 'HK.00700'
if __name__ == '__main__':
    if not on_init():
        print('Failed in on_init()')
        quote_context.close()
        trade_context.close()
    print('Do something here')
    list_accounts()
    price_step(EXAMPLE_CODE)
    list_position()
    account_info()

    test_sell_9618()
