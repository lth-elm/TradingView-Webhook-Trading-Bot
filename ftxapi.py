import logbot
import time, hmac
from requests import Request, Session, Response

class Ftx:
    def __init__(self, var: dict):
        self.ENDPOINT = 'https://ftx.com/api/'
        self.session = Session()

        self.subaccount_name = var['subaccount_name']
        self.leverage = var['leverage']
        self.risk = var['risk']
        self.api_key = var['api_key']
        self.api_secret = var['api_secret']

    # =============== SIGN, POST AND REQUEST ===============

    def _request(self, method: str, path: str, **kwargs):
        request = Request(method, self.ENDPOINT + path, **kwargs)
        self._sign_request(request)
        response = self.session.send(request.prepare())
        return self._process_response(response)

    def _sign_request(self, request: Request):
        ts = int(time.time() * 1000)
        prepared = request.prepare()
        signature_payload = f'{ts}{prepared.method}{prepared.path_url}'.encode()
        if prepared.body:
            signature_payload += prepared.body
        signature = hmac.new(self.api_secret.encode(), signature_payload, 'sha256').hexdigest()
        request.headers['FTX-KEY'] = self.api_key
        request.headers['FTX-SIGN'] = signature
        request.headers['FTX-TS'] = str(ts)
        if self.subaccount_name:
            request.headers['FTX-SUBACCOUNT'] = self.subaccount_name


    def _process_response(self, response: Response):
        try:
            data = response.json()
        except ValueError:
            response.raise_for_status()
            raise
        else:
            return data

    def _try_request(self, method: str, path: str, params=None):
        try:
            if params:
                req = self._request(method, path, json=params)
            else:
                req = self._request(method, path)
        except Exception as e:
            logbot.logs('>>> /!\ An exception occured : {}'.format(e), True)
            return {
                "success": False,
                "error": str(e)[1:-1]
            }
        if not req['success']:
            logbot.logs('>>> /!\ {}'.format(req['error']), True)
            return {
                    "success": False,
                    "error": req['error']
                }
        return req
    
    # ================== ORDER FUNCTIONS ==================

    def entry_position(self, payload: dict, ticker):
        #   PLACE ORDER
        orders = []

        side = 'buy'
        close_sl_tp_side = 'sell'
        stop_loss = payload['long SL']
        take_profit = payload['long TP']

        if payload['action'] == 'sell':
            side = 'sell'
            close_sl_tp_side = 'buy'
            stop_loss = payload['short SL']
            take_profit = payload['short TP']

        # 0/ Get free collateral and calculate position
        r = self._try_request('GET', 'account')
        if not r['success']:
            return r
        free_collateral = r['result']['freeCollateral']
        logbot.logs('>>> Found free collateral : {}'.format(free_collateral))
        size = (free_collateral * self.risk) / abs(payload['price'] - stop_loss)
        if (size / (free_collateral / payload['price'])) > 20:
            size = (free_collateral / payload['price']) * self.leverage
        
        logbot.logs(f">>> SIZE : {size}, SIDE : {side}, PRICE : {payload['price']}, SL : {stop_loss}, TP : {take_profit}")

        # 1/ for safety place market stop loss first
        sl_payload = {
            "market": ticker,
            "side": close_sl_tp_side,
            "triggerPrice": stop_loss,
            "size": size,
            "type": "stop",
            "reduceOnly": True,
            "retryUntilFilled": True
        }
        r = self._try_request('POST', 'conditional_orders', sl_payload)
        if not r['success']:
            return r
        orders.append(r['result'])
        logbot.logs(">>> Stop loss posted with success")
        
        # 2/ place order
        if 'type' in payload.keys():
            order_type = payload['type'] # 'market' or 'limit'
        else:
            order_type = 'market' # per defaut market if none is specified
        if order_type != 'market' and order_type != 'limit':
            return {
                    "success" : False,
                    "error" : f"order type '{order_type}' is unknown"
                }
        exe_price = None if order_type == "market" else payload['price']
        order_payload = {
            "market": ticker,
            "side": side,
            "price": exe_price,
            "type": order_type,
            "size": size,
            "reduceOnly": False,
            "ioc": False,
            "postOnly": False,
            "clientId": None
        }
        r = self._try_request('POST', 'orders', order_payload)
        if not r['success']:
            r['orders'] = orders
            return r
        orders.append(r['result'])
        logbot.logs(f">>> Order {order_type} posted with success")
        
        # 3/ finally the take profit only if it is not None or 0
        if take_profit:
            if order_type == 'market':
                tp_payload = {
                    "market": ticker,
                    "side": close_sl_tp_side,
                    "price": take_profit,
                    "type": "limit", # so we avoid paying fees on market take profit
                    "size": size,
                    "reduceOnly": True,
                    "ioc": False,
                    "postOnly": False,
                    "clientId": None
                }
                r = self._try_request('POST', 'orders', tp_payload)
                if not r['success']:
                    r['orders'] = orders
                    return r
                orders.append(r['result'])
                logbot.logs(">>> Take profit posted with success")
            else: # Limit order type
                tp_payload = {
                    "market": ticker,
                    "side": close_sl_tp_side,
                    "triggerPrice": exe_price,
                    "orderPrice": take_profit,
                    "size": size,
                    "type": "stop",
                    "reduceOnly": True,
                }
                r = self._try_request('POST', 'conditional_orders', tp_payload)
                if not r['success']:
                    r['orders'] = orders
                    return r
                orders.append(r['result'])
                logbot.logs(">>> Take profit posted with success")
        
        # 4/ (optional) place multiples take profits
        i = 1
        while True:
            tp = 'tp' + str(i) + ' Mult'
            if tp in payload.keys():
                # place limit order
                dist = abs(payload['price'] - stop_loss) * payload[tp]
                mid_take_profit = (payload['price'] + dist) if  side == 'buy' else (payload['price'] - dist)
                mid_size = size * (payload['tp Close'] / 100)
                if order_type == 'market':
                    tp_payload = {
                        "market": ticker,
                        "side": close_sl_tp_side,
                        "price": mid_take_profit,
                        "type": "limit", # so we avoid paying fees on market take profit
                        "size": mid_size,
                        "reduceOnly": True,
                        "ioc": False,
                        "postOnly": False,
                        "clientId": None
                    }
                    r = self._try_request('POST', 'orders', tp_payload)
                    if not r['success']:
                        r['orders'] = orders
                        return r
                    orders.append(r['result'])
                    logbot.logs(f">>> Take profit {i} posted with success at price {mid_take_profit} with size {mid_size}")
                else: # Stop limit type
                    tp_payload = {
                        "market": ticker,
                        "side": close_sl_tp_side,
                        "triggerPrice": exe_price,
                        "orderPrice": mid_take_profit,
                        "size": mid_size,
                        "type": "stop",
                        "reduceOnly": True,
                    }
                    r = self._try_request('POST', 'conditional_orders', tp_payload)
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
        #   CLOSE POSITION IF ONE IS ONGOING
        r = self._try_request('GET', 'positions')
        if not r['success']:
            return r
        logbot.logs(">>> Retrieve positions")

        for position in r['result']:
            if position['future'] == ticker:
                open_size = position['size']
                open_side = position['side']

                if open_size: # position is open so close it
                    close_side = 'sell' if open_side == 'buy' else 'buy'
                    close_order_payload = {
                    "market": ticker,
                    "side": close_side,
                    "price": None,
                    "type": "market",
                    "size": open_size,
                    "reduceOnly": True,
                    "ioc": False,
                    "postOnly": False,
                    "clientId": None
                    }

                    r = self._try_request('POST', 'orders', close_order_payload)
                    if not r['success']:
                        return r
                    logbot.logs(">>> Close ongoing position with success")

                break

        #   DELETE ALL OPEN AND CONDITIONAL ORDERS REMAINING
        r = self._try_request('DELETE', 'orders')
        if not r['success']:
            return r
        logbot.logs(">>> Deleted all open and conditional orders remaining with success")
        
        return {
            "success": True
        }


    def breakeven(self, payload: dict, ticker):
        #   SET STOP LOSS TO BREAKEVEN
        r = self._try_request('GET', 'positions')
        if not r['success']:
            return r
        logbot.logs(">>> Retrieve positions")

        orders = []

        for position in r['result']:
            if position['future'] == ticker:
                open_size = position['openSize']
                open_side = position['side']

                if open_size: # position is still open (and should be)
                    close_side = 'sell' if open_side == 'buy' else 'buy'
                    breakeven_price = payload['long Breakeven'] if open_side == 'buy' else payload['short Breakeven']

                    # place market stop loss at breakeven
                    breakeven_sl_payload = {
                        "market": ticker,
                        "side": close_side,
                        "triggerPrice": breakeven_price,
                        "size": open_size,
                        "type": "stop",
                        "reduceOnly": True,
                        "retryUntilFilled": True
                    }
                    r = self._try_request('POST', 'conditional_orders', breakeven_sl_payload)
                    if not r['success']:
                        return r
                    orders.append(r['result'])
                    logbot.logs(f">>> Breakeven stop loss posted with success at price {breakeven_price}")

        return {
            "success": True,
            "orders": orders
        }
