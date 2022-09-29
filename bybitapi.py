import logbot
from pybit import HTTP

class ByBit:
    def __init__(self, var: dict):
        self.ENDPOINT = 'https://api.bybit.com'
        self.subaccount_name = var['subaccount_name']
        self.leverage = var['leverage']
        self.risk = var['risk']
        self.api_key = var['api_key']
        self.api_secret = var['api_secret']
        
    # =============== SIGN, POST AND REQUEST ===============

    def _try_request(self, method: str, **kwargs):
        session = HTTP(self.ENDPOINT, api_key=self.api_key, api_secret=self.api_secret)
        try:
            if method == "api_key_info":
                req = session.api_key_info() #Check if Referral Link is USED
            if method == 'set_leverage':
                req = session.set_leverage(symbol=kwargs.get('symbol'), 
                                                buy_leverage=kwargs.get('sell_leverage'),
                                                sell_leverage=kwargs.get('buy_leverage'))
            if method == 'cross_isolated_margin_switch':
                req = session.cross_isolated_margin_switch(symbol=kwargs.get('symbol'),
                                                            is_isolated=kwargs.get('is_isolated'), 
                                                            buy_leverage=kwargs.get('sell_leverage'),
                                                            sell_leverage=kwargs.get('buy_leverage'))
            if method=='get_wallet_balance':
                req = session.get_wallet_balance(coin=kwargs.get('coin'))
            elif method=='my_position':
                req = session.my_position(symbol=kwargs.get('symbol'))
            elif method=='place_active_order':
                req = session.place_active_order(symbol=kwargs.get('symbol'), 
                                                    side=kwargs.get('side'), 
                                                    order_type=kwargs.get('order_type'), 
                                                    qty=kwargs.get('qty'), 
                                                    price=kwargs.get('price', None), 
                                                    stop_loss=kwargs.get('stop_loss', None), 
                                                    time_in_force=kwargs.get('time_in_force'), 
                                                    reduce_only=kwargs.get('reduce_only'), 
                                                    close_on_trigger=kwargs.get('close_on_trigger'))
            elif method=='place_conditional_order':
                req = session.place_conditional_order(symbol=kwargs.get('symbol'),
                                                        side=kwargs.get('side'),
                                                        order_type=kwargs.get('order_type'),
                                                        qty=kwargs.get('qty'),
                                                        price=kwargs.get('price'),
                                                        base_price=kwargs.get('base_price'),
                                                        stop_px=kwargs.get('stop_px'),
                                                        trigger_by=kwargs.get('trigger_by'),
                                                        time_in_force=kwargs.get('time_in_force'),
                                                        reduce_only=kwargs.get('reduce_only'),
                                                        close_on_trigger=kwargs.get('close_on_trigger'))
            elif method=='cancel_all_active_orders':
                req = session.cancel_all_active_orders(symbol=kwargs.get('symbol'))
            elif method=='cancel_all_conditional_orders':
                req = session.cancel_all_conditional_orders(symbol=kwargs.get('symbol'))
            elif method=='set_trading_stop':
                req = session.set_trading_stop(symbol=kwargs.get('symbol'), 
                                                side=kwargs.get('side'), # Side of the open position
                                                stop_loss=kwargs.get('stop_loss'))
            elif method=='query_symbol':
                req = session.query_symbol()
        except Exception as e:
            logbot.logs('>>> /!\ An exception occured : {}'.format(e), True)
            return {
                "success": False,
                "error": str(e)
            }
        if req['ret_code']:
            logbot.logs('>>> /!\ {}'.format(req['ret_msg']), True)
            return {
                    "success": False,
                    "error": req['ret_msg']
                }
        else:
            req['success'] = True
        return req
    # ================== UTILITY FUNCTIONS ==================

    def _rounded_size(self, size, qty_step):
        step_size = round(float(size) / qty_step) * qty_step
        if isinstance(qty_step, float):
            decimal = len(str(qty_step).split('.')[1])
            return round(step_size, decimal)
        return step_size
    
    # ================== ORDER FUNCTIONS ==================

    def entry_position(self, payload: dict, ticker):
        # r = self._try_request('api_key_info')  
        # r = r['result']
        # r = next((item for item in r if item['inviter_id'] == (161092600,130095514711 )), None)
        # r = r['inviter_id']
        # if r == True:
        #     logbot.logs('>>> Account succesfully using referral')
        #     pass
        # else:
        #     return {
        #             "success": False,
        #             "error": '>>> Account NOT using referral'
        #         }
        
        #   PLACE ORDER 
        #   USE TESTNET OR NOT   
        if 'testnet' in payload.keys():
            endpoint = payload['testnet'] 
            if endpoint == True:
                self.ENDPOINT = "https://api-testnet.bybit.com"
            else:
                endpoint = False
        #   CHANGE LEVERAGE    
        if 'leverage' in payload.keys():
            leverage = payload['leverage']
            self._try_request('set_leverage', symbol=ticker, buy_leverage=leverage ,sell_leverage=leverage)
        else:
            leverage = None
            
        if 'isolated' in payload.keys():
            isolated = payload['isolated']
            self._try_request('cross_isolated_margin_switch', symbol=ticker, is_isolated=isolated, buy_leverage=leverage ,sell_leverage=leverage)
        else:
            isolated = False
            
        orders = []
        close_sl_tp_side = None
        stop_loss = None
        take_profit = None
        
        if payload['action'] == 'Buy':
            side = 'Buy'
            close_sl_tp_side = 'Sell'
            stop_loss = payload['long SL']
            take_profit = payload['long TP']

        if payload['action'] == 'sell':
            side = 'Sell'
            close_sl_tp_side = 'Buy'
            stop_loss = payload['short SL']
            take_profit = payload['short TP']
        
        
        r = self._try_request('query_symbol')
        r = r['result']
        my_item = next((item for item in r if item['name'] == 'BTCUSDT'), None)
        qty_step = my_item['lot_size_filter']['qty_step']

        # 0/ Get free collateral and calculate position
        r = self._try_request('get_wallet_balance', coin="USDT")
        if not r['success']:
            return r
        free_collateral = r['result']['USDT']['available_balance']
        
        # Calculate amount of collateral to use %
        if 'amount' in payload.keys():
            amount = payload['amount']
            self.risk = float(amount) / 100
        else:
            amount = None

        logbot.logs('>>> Found free collateral : {}'.format(free_collateral))
        # size = (free_collateral * self.risk) / abs(payload['price'] - stop_loss) 
        times_symbol = (abs(payload['price'] / (free_collateral * self.risk)))
        size_symbol = 1 / times_symbol
        size = size_symbol * payload['leverage']
                        
        if (size / (free_collateral / payload['price'])) > self.leverage:
            return {
                    "success" : False,
                    "error" : "leverage is higher than maximum limit you set"
                }
        
        size = self._rounded_size(size, qty_step)

        logbot.logs(f">>> SIZE : {size}, SIDE : {side}, LEVERAGE : {payload['leverage']} PRICE : {payload['price']}, SL : {stop_loss}, TP : {take_profit}")
     
        # 1/ place order with stop loss
        if 'type' in payload.keys():
            order_type = payload['type'] # 'market' or 'limit'
            order_type = order_type.capitalize()
        else:
            order_type = 'Market' # per defaut market if none is specified
        if order_type != 'Market' and order_type != 'Limit':
            return {
                    "success" : False,
                    "error" : f"order type '{order_type}' is unknown"
                }
        exe_price = None if order_type == "Market" else payload['price']
        r = self._try_request('place_active_order', 
                            symbol=ticker, 
                            side=side, 
                            order_type=order_type, 
                            qty=size, 
                            price=exe_price, 
                            stop_loss=stop_loss, 
                            time_in_force="GoodTillCancel", 
                            reduce_only=False, 
                            close_on_trigger=False)
        if not r['success']:
            r['orders'] = orders
            return r
        orders.append(r['result'])
        logbot.logs(f">>> Order {order_type} posted with success")
        
        # 2/ place the take profit only if it is not None or 0
        if take_profit:
            if order_type == 'Market':
                r = self._try_request('place_active_order', 
                                    symbol=ticker, 
                                    side=close_sl_tp_side, 
                                    order_type="Limit", # so we avoid paying fees on market take profit
                                    qty=size, 
                                    price=take_profit,
                                    time_in_force="GoodTillCancel", 
                                    reduce_only=True, 
                                    close_on_trigger=False)
                if not r['success']:
                    r['orders'] = orders
                    return r
                orders.append(r['result'])
                logbot.logs(">>> Take profit posted with success")
            else: # Limit order type
                r = self._try_request('place_conditional_order', 
                                    symbol=ticker, 
                                    side=close_sl_tp_side, 
                                    order_type="Limit", 
                                    qty=size, 
                                    price=take_profit, 
                                    base_price=exe_price, 
                                    stop_px=exe_price, 
                                    trigger_by='LastPrice', 
                                    time_in_force="GoodTillCancel", 
                                    reduce_only=False, # Do not set to True
                                    close_on_trigger=False)
                if not r['success']:
                    r['orders'] = orders
                    return r
                orders.append(r['result'])
                logbot.logs(">>> Take profit posted with success")
        
        # 3/ (optional) place multiples take profits
        i = 1
        while True:
            tp = 'tp' + str(i) + ' Mult'
            if tp in payload.keys():
                # place limit order
                dist = abs(payload['price'] - stop_loss) * payload[tp]
                mid_take_profit = (payload['price'] + dist) if  side == 'Buy' else (payload['price'] - dist)
                mid_size = size * (payload['tp Close'] / 100)
                mid_size = self._rounded_size(mid_size, qty_step)
                if order_type == 'Market':
                    r = self._try_request('place_active_order', 
                            symbol=ticker, 
                            side=close_sl_tp_side, 
                            order_type="Limit", # so we avoid paying fees on market take profit
                            qty=mid_size, 
                            price=mid_take_profit,
                            time_in_force="GoodTillCancel", 
                            reduce_only=True, 
                            close_on_trigger=False)
                    if not r['success']:
                        r['orders'] = orders
                        return r
                    orders.append(r['result'])
                    logbot.logs(f">>> Take profit {i} posted with success at price {mid_take_profit} with size {mid_size}")
                else: # Stop limit type
                    r = self._try_request('place_conditional_order', 
                                    symbol=ticker, 
                                    side=close_sl_tp_side, 
                                    order_type="Limit", 
                                    qty=mid_size, 
                                    price=mid_take_profit, 
                                    base_price=exe_price, 
                                    stop_px=exe_price, 
                                    trigger_by='LastPrice', 
                                    time_in_force="GoodTillCancel", 
                                    reduce_only=False, # Do not set to True
                                    close_on_trigger=False)
                    if not r['success']:
                        r['orders'] = orders
                        return r
                    orders.append(r['result'])
                    logbot.logs(f">>> Take profit {i} posted with success at price {mid_take_profit} with size {mid_size}")
            else:
                break
            i += 1
        
        return {
            "success": True,
            "orders": orders
        }


    def exit_position(self, ticker):
        # if 'testnet' in payload.keys():
        #     endpoint = payload['testnet'] 
        #     endpoint = endpoint.capitalize()
        #     if endpoint == 'True':
        #         self.ENDPOINT = "https://api-testnet.bybit.com"
        #     else:
        #         endpoint = 'False'
        
        #   CLOSE POSITION IF ONE IS ONGOING
        r = self._try_request('my_position', symbol=ticker)
        if not r['success']:
            return r
        logbot.logs(">>> Retrieve positions")

        for position in r['result']:
            open_size = position['size']
            if open_size > 0:
                open_side = position['side']
                close_side = 'Sell' if open_side == 'Buy' else 'Buy'
                
                r = self._try_request('place_active_order', 
                                    symbol=ticker,
                                    side=close_side,
                                    order_type="Market",
                                    qty=open_size,
                                    price=None,
                                    time_in_force="GoodTillCancel",
                                    reduce_only=True,
                                    close_on_trigger=False)

                if not r['success']:
                    return r
                logbot.logs(">>> Close ongoing position with success")

                break

        #   DELETE ALL OPEN AND CONDITIONAL ORDERS REMAINING
        r = self._try_request('cancel_all_active_orders', symbol=ticker)
        if not r['success']:
            return r
        r = self._try_request('cancel_all_conditional_orders', symbol=ticker)
        if not r['success']:
            return r
        logbot.logs(">>> Deleted all open and conditional orders remaining with success")
        
        return {
            "success": True
        }


    def breakeven(self, payload: dict, ticker):
        if 'testnet' in payload.keys():
            endpoint = payload['testnet'] 
            if endpoint == True:
                self.ENDPOINT = "https://api-testnet.bybit.com"
            else:
                endpoint = False
        
        #   SET STOP LOSS TO BREAKEVEN
        r = self._try_request('my_position', symbol=ticker)
        if not r['success']:
            return r
        logbot.logs(">>> Retrieve positions")

        orders = []

        for position in r['result']:
            open_size = position['size']
            if open_size > 0:
                open_side = position['side']
                # close_side = 'Sell' if open_side == 'Buy' else 'Buy'
                breakeven_price = payload['long Breakeven'] if open_side == 'Buy' else payload['short Breakeven']

                # place market stop loss at breakeven
                r = self._try_request('set_trading_stop', 
                                    symbol=ticker, 
                                    side=open_side, # Side of the open position
                                    stop_loss=breakeven_price)
                if not r['success']:
                    return r
                orders.append(r['result'])
                logbot.logs(f">>> Breakeven stop loss posted with success at price {breakeven_price}")

        return {
            "success": True,
            "orders": orders
        }
