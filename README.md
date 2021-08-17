**Rough version...**

*Flask app receiving alerts from TradingView and automatically sends a POST order to an integrated exchange API such as FTX (Binance and ByBit to come). Can also deliver the alert and the chart to discord where you can decide whether or not to take that trade through a Discord bot.*


*TABLE OF CONTENT*


In order to build that app I relied on two great videos to get started, implementing and deploying basics stuff, I then enhanced it all for my own use. This one from Part Time Larry https://www.youtube.com/watch?v=XPTb3adEQEE (his [github](https://github.com/hackingthemarkets)) and this one for the discord bot from freeCodeCamp.org : https://www.youtube.com/watch?v=SPTfmiYiuok.


I won't go into full details so if you're a novice you might want to go through the videos first (at least the first one for the first part) but not necessary if you only want to take a grasp of what's happening here, otherwise if you already master even a bit of Flask, APIs, webhooks and TradingView pinescripts you can easily follow along.  ...?... (I will try to add more technical explanations over time or a glossary)


Fist of all, to be able to use TradingView webhooks you will need to subscribe to the pro plan for approximately 12$ per month (a free month trial is available), and you can use my referral link to sign up so we all save 30$ when upgrading to a paid plan : https://www.tradingview.com/gopro/?share_your_love=lth_elm.


Now that this is done we can get down to business. We will need to write a pinescript strategy that will be for our example focused on **mean reversions** : if we are above/under the 200 period EMA, RSI is overbought/oversold and we have a bearish/bullish engulfing candle we will either short or long the position trying to come back to the 200 period exponential moving average. For ease of use the stop-losses and take-profits are placed using "random" values of ATR.

[Here](pinestrategies/Quick-Mean-Reversion-Strat.pine) is the script that I wrote you can have a look. I added my own touch so I can visualize the stop-loss and take-profit targets on chart.

*Of course it is far from being perfect so don't use it for you own trading since it wasn't written for this purpose and it's a strategy going against the main trend (thus very risky). **However we will see in part 2 how we can improve it and integrate our own choice thanks to the discord bot.***

![Mean reversion strategy BTCPERP](./README_images/MeanReversionStrategyBTCPERP.png "Mean reversion strategy BTCPERP")

As you can see we have multiples exit positions and some are even at breakeven, our integration with the FTX api is compatible for this style of trading, you can set the % you want to close for these intermediary TP in the ```tp_close``` variable. 

However, if you want to keep it to the bottom line you can just set **one entry** and **one fixed exit**. For that you will need to uncomment the ```strategy.exit()``` lines for both ```if goLong``` and ```if goShort``` and remove the two following lines:

```pinescript
// Execute buy or sell order
if goLong and notInTrade
    size = (strategy.equity*risk) / abs(close-long_stop_level)
    strategy.entry("long", strategy.long, qty=size, alert_message="entry")
    // strategy.exit("exit", "long", stop=long_stop_level, limit=long_profit_level, alert_message="exit")
    inLongPosition := true // to remove
    notInTrade := false // to remove
```

And delete all the *multiple TP* category.

```pinescript
// ----- MULTIPLE TP -----
// ...
```
___

When deciding to take, close or exit a position with **strategy.*entry/close/exit*()** you must specify an **'alert_message'** that can only be one of those : ```entry``` | ```exit``` for the minimal basic strategy, ```tp[n]``` if you've set multiple take profit level and finally ```xxx_breakeven``` anything can be written before the letter 'b' this is just for when this alert is triggered the bot will set a new stop-loss at breakeven level (+ a few % to save comission fees).


*SET THE ALERT WITH THE MESSAGE AS A JSON + PASSPHRASE + PLACEHOLDER + WEBHOOK URL*

*THEN FLASK APP*



*At the end all referral links for website used*