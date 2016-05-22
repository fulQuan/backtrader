#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
#
# Copyright (C) 2015,2016 Daniel Rodriguez
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import argparse
import datetime

# The above could be sent to an independent module
import backtrader as bt
import backtrader.feeds as btfeeds
import backtrader.brokers as btbrokers
import backtrader.indicators as btind
from backtrader.utils import flushfile


class EmptyStrategy(bt.Strategy):
    params = dict(smaperiod=15)

    def __init__(self):
        # To control operation entries
        self.orderid = list()

        # Create SMA on 2nd data
        self.sma = btind.MovAv.SMA(self.data, period=self.p.smaperiod)

        print('--------------------------------------------------')
        print('Strategy Created')
        print('--------------------------------------------------')

    def prenext(self):
        self.next(frompre=True)

    def next(self, frompre=False):
        txt = list()
        txt.append('%04d' % len(self))
        dtfmt = '%Y-%m-%dT%H:%M:%S.%f'
        txt.append('%s' % self.data.datetime.datetime(0).strftime(dtfmt))
        txt.append('%.2f' % self.data.open[0])
        txt.append('%.2f' % self.data.high[0])
        txt.append('%.2f' % self.data.low[0])
        txt.append('%.2f' % self.data.close[0])
        txt.append('%d' % self.data.volume[0])
        txt.append('%d' % self.data.openinterest[0])
        txt.append('%.2f' % (self.sma[0]))
        print(', '.join(txt))

        if len(self.datas) > 1:
            txt = list()
            txt.append('%04d' % len(self))
            dtfmt = '%Y-%m-%dT%H:%M:%S.%f'
            txt.append('%s' % self.data1.datetime.datetime(0).strftime(dtfmt))
            txt.append('%.2f' % self.data1.open[0])
            txt.append('%.2f' % self.data1.high[0])
            txt.append('%.2f' % self.data1.low[0])
            txt.append('%.2f' % self.data1.close[0])
            txt.append('%d' % self.data1.volume[0])
            txt.append('%d' % self.data1.openinterest[0])
            # txt.append('%.2f' % (self.sma1[0]))
            txt.append('%.2f' % float('NaN'))
            print(', '.join(txt))

        if self.done:
            return

        if not self.position or len(self.orderid) < 1:
            order = self.buy(size=20,
                             exectype=bt.Order.Market,
                             price=self.data0.close[0])
            self.orderid.append(order)
        else:
            self.sell(size=self.position.size + 200,
                      exectype=bt.Order.Market,
                      price=self.data0.close[0])

            self.done = True

    def start(self):
        header = ['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume',
                  'OpenInterest', 'SMA']
        print(', '.join(header))

        self.done = False


def runstrategy():
    args = parse_args()

    # Create a cerebro
    cerebro = bt.Cerebro()

    if args.broker:
        b = btbrokers.IBBroker(port=args.port, _debug=args.debug)
        cerebro.setbroker(b)

    # Create the 1st data
    if args.tz:
        import pytz
        tz = pytz.timezone(args.tz)
    else:
        tz = None

    data0 = btfeeds.IBData(dataname=args.data0,
                           port=args.port,
                           useRT=args.rtbar,
                           tz=tz,
                           _debug=args.debug,
                           timeframe=bt.TimeFrame.Ticks)

    if args.data1 is None:
        data1 = None
    else:
        data1 = btfeeds.IBData(dataname='AAPL-STK-SMART-USD',
                               port=args.port,
                               useRT=args.rtbar,
                               tz=tz,
                               _debug=args.debug,
                               timeframe=bt.TimeFrame.Ticks)

    bar2edge = not args.nobar2edge
    adjbartime = not args.noadjbartime
    rightedge = not args.norightedge

    if args.replay:
        cerebro.replaydata(dataname=data0,
                           timeframe=bt.TimeFrame.Seconds,
                           compression=args.compression,
                           bar2edge=bar2edge,
                           adjbartime=adjbartime,
                           rightedge=rightedge)
        if data1 is not None:
            cerebro.replaydata(dataname=data1,
                               timeframe=bt.TimeFrame.Seconds,
                               compression=args.compression,
                               bar2edge=bar2edge,
                               adjbartime=adjbartime,
                               rightedge=rightedge)
    elif args.resample:
        cerebro.resampledata(dataname=data0,
                             timeframe=bt.TimeFrame.Seconds,
                             compression=args.compression,
                             bar2edge=bar2edge,
                             adjbartime=adjbartime,
                             rightedge=rightedge)

        if data1 is not None:
            cerebro.resampledata(dataname=data1,
                                 timeframe=bt.TimeFrame.Seconds,
                                 compression=args.compression,
                                 bar2edge=bar2edge,
                                 adjbartime=adjbartime,
                                 rightedge=rightedge)
    else:
        cerebro.adddata(data0)
        if data1 is not None:
            cerebro.adddata(data1)

    # Add the strategy
    cerebro.addstrategy(EmptyStrategy, smaperiod=args.smaperiod)

    # Live data ... avoid long data accumulation by switching to "exactbars"
    cerebro.run(exactbars=1)


def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Test IB Realtime Data Feed')

    parser.add_argument('--data0', required=False, default='IBKR',
                        help='data into the system')

    parser.add_argument('--data1', action='store', default=None,
                        help='data into the system')

    parser.add_argument('--port', default=7496, type=int,
                        help='Port for the Interactive Brokers TWS Connection')

    parser.add_argument('--rtbar', required=False, action='store_true',
                        help=('Use 5 seconds real time bar updates'))

    parser.add_argument('--debug', required=False, action='store_true',
                        help=('Display all info received form IB'))

    parser.add_argument('--seeprint', required=False, action='store_true',
                        help=('See IbPy initial print messages'))

    parser.add_argument('--smaperiod', default=5, type=int,
                        help='Period to apply to the Simple Moving Average')

    pgroup = parser.add_mutually_exclusive_group(required=False)

    pgroup.add_argument('--replay', required=False, action='store_true',
                        help=('replay to minutes'))

    pgroup.add_argument('--resample', required=False, action='store_true',
                        help=('resample to minutes'))

    parser.add_argument('--compression', default=1, type=int,
                        help='Compression level for resample/replay')

    parser.add_argument('--nobar2edge', required=False, action='store_true',
                        help=('no bar2edge'))

    parser.add_argument('--noadjbartime', required=False, action='store_true',
                        help=('noadjbartime'))

    parser.add_argument('--norightedge', required=False, action='store_true',
                        help=('rightedge'))

    parser.add_argument('--tz', required=False,
                        help=('Timezone in pytz format. Ex: "US/Eastern"'))

    parser.add_argument('--broker', required=False, action='store_true',
                        help=('Use IB as broker'))

    return parser.parse_args()


if __name__ == '__main__':
    runstrategy()