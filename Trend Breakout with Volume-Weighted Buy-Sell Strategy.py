

from AlgoAPI import AlgoAPIUtil, AlgoAPI_Backtest
from datetime import datetime, timedelta

class AlgoEvent:
    def __init__(self, timeinforce=86400):
        self.price_changes = []
        self.volumes = []
        self.close_prices = []
        self.trend_labels = []  # list of (timestamp, trend_value, close_price)
        self.buyPrice = None
        self.sellPrice = None
        self.lows_base_count = 0
        self.lows_peak_count = 0
        self.prev_peak_count = None  # for sell signal detection
        self.buySignal_active = False  # flag to control sell logic
        self.volume_spike_signals = []
        self.buy_with_volume_signals = []
        self.initial_capital = 100000.0
        self.available_capital = 100000.0
        self.timeinforce = timeinforce
        self.net_volume = 0

    def start(self, mEvt):
        self.evt = AlgoAPI_Backtest.AlgoEvtHandler(self, mEvt)
        self.myinstrument = mEvt['subscribeList'][0]
        self.lastprice = None
        self.evt.start()

    def detect_downtrend(self, prices):
        if len(prices) < 2:
            return False
        highs, lows = [], []
        if prices[0] <= prices[1]:
            lows.append(prices[0])
            highs.append(prices[1])
        else:
            lows.append(prices[1])
            highs.append(prices[0])
        for value in prices[2:]:
            if value < lows[-1]:
                lows.append(value)
            elif value < highs[-1]:
                highs.append(value)
            else:
                return False
        return True

    def detect_uptrend(self, prices):
        if len(prices) < 2:
            return False
        highs, lows = [], []
        if prices[0] >= prices[1]:
            highs.append(prices[0])
            lows.append(prices[1])
        else:
            highs.append(prices[1])
            lows.append(prices[0])
        for value in prices[2:]:
            if value > highs[-1]:
                highs.append(value)
            elif value > lows[-1]:
                lows.append(value)
            else:
                return False
        return True

    def get_macro_uptrend_lows(self):
        breakpoints = []
        i = len(self.trend_labels) - 1
        current_breakpoint = None
        while i >= 0:
            if self.trend_labels[i][1] == 1:
                i -= 1
                continue
            temp_segment = []
            while i >= 0 and self.trend_labels[i][1] in [0, -1]:
                price = self.trend_labels[i][2]
                timestamp = self.trend_labels[i][0]
                temp_segment.append((price, timestamp))
                i -= 1
            if not temp_segment:
                continue
            lowest_price, low_timestamp = min(temp_segment, key=lambda x: x[0])
            if current_breakpoint is None or lowest_price <= current_breakpoint[0]:
                current_breakpoint = (lowest_price, low_timestamp)
                breakpoints.append(current_breakpoint)
        return breakpoints[::-1]

    def get_macro_uptrend_highs(self):
        highs = []
        i = len(self.trend_labels) - 1
        current_high = None
        while i >= 0:
            temp_segment = []
            uptrend_count = 0
            expect_uptrend = False
            while i >= 0:
                label = self.trend_labels[i][1]
                price = self.trend_labels[i][2]
                timestamp = self.trend_labels[i][0]
                if label in [-1, 0]:
                    if uptrend_count > 0:
                        temp_segment.append((price, timestamp))
                        i -= 1
                        break
                    else:
                        temp_segment.append((price, timestamp))
                        i -= 1
                        expect_uptrend = True
                        continue
                if label == 1:
                    if expect_uptrend:
                        temp_segment.append((price, timestamp))
                        if uptrend_count > 0:
                            break
                        uptrend_count += 1
                        i -= 1
                    else:
                        if uptrend_count > 0:
                            break
                        i -= 1
            if not temp_segment:
                continue
            highest_price, high_timestamp = max(temp_segment, key=lambda x: x[0])
            if current_high is None or highest_price <= current_high[0]:
                current_high = (highest_price, high_timestamp)
                highs.append(current_high)
            else:
                break
        return highs[::-1]

    def check_buy_pattern(self, lows, highs):
        if len(lows) >= 3 and len(highs) >= 2:
            l1, l2, l3 = lows[-3:]
            h1, h2 = highs[-2:]
            if l1[1] < h1[1] < l2[1] < h2[1] < l3[1]:
                return True
        return False

    def check_volume_spike_sell_signal(self, current_volume, open_price, current_price, high_price, low_price):
        if len(self.volumes) < 3:
            return False
        avg_volume = sum(self.volumes[-3:]) / 3
        if current_volume > 1.05 * avg_volume:
            if current_price > open_price:
                if self.net_volume > 0:
                    order = AlgoAPIUtil.OrderObject()
                    order.instrument = self.myinstrument
                    order.orderRef = int(datetime.now().timestamp())
                    order.openclose = 'close'
                    order.orderRef = 'spike'
                    order.buysell = -1
                    order.ordertype = 2  # limit
                    order.price = current_price
                    order.volume = self.net_volume
                    order.timeinforce = self.timeinforce
                    self.evt.sendOrder(order)
                    self.evt.consoleLog(f"LIMIT SELL ORDER: {self.net_volume} units @ {current_price}")
                return True
        return False

    def can_buy_with_volume(self, current_price, lows, highs, open_price, high_price, low_price):
        if not self.check_buy_pattern(lows, highs):
            return 0

        if self.check_volume_spike_sell_signal(self.volumes[-1], open_price, current_price, high_price, low_price):
            self.volume_spike_signals.append((self.trend_labels[-1][0], current_price))
            return 0

        last_buy = self.buy_with_volume_signals[-1][1] if self.buy_with_volume_signals else None

        if last_buy is not None and current_price < last_buy:
            capital_to_use = 0.05 * self.available_capital
            self.evt.consoleLog(f"--5%--")
        else:
            capital_to_use = 0.03 * self.available_capital
            self.evt.consoleLog(f"--3%--")

        volume_to_buy = round(capital_to_use / current_price)
        self.buy_with_volume_signals.append((self.trend_labels[-1][0], current_price))

        eight_percent_price = 0.08 * current_price
        second_last_low = lows[-2][0] if len(lows) >= 2 else 0
        stop_loss = current_price - max(eight_percent_price, current_price - second_last_low)

        order = AlgoAPIUtil.OrderObject()
        order.instrument = self.myinstrument
        order.orderRef = int(datetime.now().timestamp())
        order.openclose = 'open'
        order.buysell = 1
        order.ordertype = 0  # limit order
        order.price = current_price
        order.volume = volume_to_buy
        order.stopLossLevel = stop_loss
        order.timeinforce = self.timeinforce

        self.evt.sendOrder(order)

        self.evt.consoleLog(f"LIMIT BUY ORDER: {volume_to_buy:.0f} units @ {current_price}, Stop Loss: {stop_loss:.2f}")
        return volume_to_buy

    def on_bulkdatafeed(self, isSync, bd, ab):
        if self.myinstrument not in bd:
            return

        timestamp = bd[self.myinstrument]['timestamp']
        current_price = bd[self.myinstrument]['lastPrice']
        current_volume = bd[self.myinstrument]['volume']
        openPrice = bd[self.myinstrument]['openPrice']
        highPrice = bd[self.myinstrument]['highPrice']
        lowPrice = bd[self.myinstrument]['lowPrice']

        self.available_capital = ab['availableBalance']

        self.evt.consoleLog(
            f"{timestamp}: Open = {openPrice:.2f} | Close = {current_price:.2f} | High = {highPrice:.2f} | Low = {lowPrice:.2f} | Volume: {current_volume}"
        )

        if self.lastprice is not None:
            diff = current_price - self.lastprice
            self.price_changes.append(diff)
            self.volumes.append(current_volume)
            self.close_prices.append(current_price)

            if len(self.close_prices) >= 4:
                trend_window = self.close_prices[-4:]
                if self.detect_uptrend(trend_window):
                    self.trend_labels.append((timestamp, 1, current_price))
                elif self.detect_downtrend(trend_window):
                    self.trend_labels.append((timestamp, 0, current_price))
                else:
                    self.trend_labels.append((timestamp, -1, current_price))

            lows = self.get_macro_uptrend_lows()
            highs = self.get_macro_uptrend_highs()

            current_low_count = len(lows)

            if current_low_count > self.lows_peak_count:
                self.prev_peak_count = self.lows_peak_count
                self.lows_peak_count = current_low_count

            if self.prev_peak_count is not None and current_low_count - self.prev_peak_count <= -1:
                self.sellPrice = current_price
                self.buySignal_active = False
                self.evt.consoleLog("SELL ALL")
                if self.net_volume > 0:
                    order = AlgoAPIUtil.OrderObject()
                    order.instrument = self.myinstrument
                    order.orderRef = int(datetime.now().timestamp())
                    order.openclose = 'close'
                    order.orderRef = 'forced'
                    order.buysell = -1
                    order.ordertype = 0  # market order
                    order.volume = self.net_volume
                    order.timeinforce = self.timeinforce
                    self.evt.sendOrder(order)
                    self.evt.consoleLog(f"MARKET SELL ORDER: {self.net_volume} units")
                self.prev_peak_count = current_low_count

            if self.check_volume_spike_sell_signal(current_volume, openPrice, current_price, highPrice, lowPrice) and self.buySignal_active:
                self.sellPrice = current_price
                self.buySignal_active = False
                self.evt.consoleLog(f"Volume spike SELL SIGNAL at Price = {current_price}")

            self.can_buy_with_volume(current_price, lows, highs, openPrice, highPrice, lowPrice)

        self.lastprice = current_price

    def on_marketdatafeed(self, md, ab):
        pass
    def on_newsdatafeed(self, nd):
        pass
    def on_weatherdatafeed(self, wd):
        pass
    def on_econsdatafeed(self, ed):
        pass
    def on_corpAnnouncement(self, ca):
        pass
    def on_orderfeed(self, of):
        pass
    def on_dailyPLfeed(self, pl):
        pass
    def on_openPositionfeed(self, op, oo, uo):
        if self.myinstrument in op:
            self.net_volume = op[self.myinstrument]['netVolume']




