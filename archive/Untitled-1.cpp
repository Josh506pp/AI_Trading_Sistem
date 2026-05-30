//+------------------------------------------------------------------+
//|                    Algorithmic Trading Bot                       |
//|                        for MetaTrader 5                          |
//+------------------------------------------------------------------+
#include "Trade/Trade.mqh"
// Note: This code is designed for MetaTrader 5 and should be compiled in MetaEditor
#property strict

// Input parameters
input double RiskPercent = 2.0;           // Risk per trade (%)
input int FastMA = 10;                   // Fast Moving Average
input int SlowMA = 20;                   // Slow Moving Average
input double TakeProfitPoints = 100;     // Take Profit in points
input double StopLossPoints = 50;        // Stop Loss in points

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
    if(FastMA <= 0 || SlowMA <= 0 || FastMA >= SlowMA)
    {
        Print("Invalid MA input values. FastMA must be >0, SlowMA >0 and FastMA < SlowMA.");
        return(INIT_PARAMETERS_INCORRECT);
    }
    return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Tick function                                                     |
//+------------------------------------------------------------------+
void OnTick()
{
    // Ensure we have enough bars
    if(Bars(Symbol(), PERIOD_CURRENT) <= SlowMA + 2)
        return;

    // Calculate Moving Averages (current and previous bar)
    double fastMA_Current = iMA(Symbol(), PERIOD_CURRENT, FastMA, 0, MODE_SMA, PRICE_CLOSE, 0);
    double slowMA_Current = iMA(Symbol(), PERIOD_CURRENT, SlowMA, 0, MODE_SMA, PRICE_CLOSE, 0);
    double fastMA_Previous = iMA(Symbol(), PERIOD_CURRENT, FastMA, 0, MODE_SMA, PRICE_CLOSE, 1);
    double slowMA_Previous = iMA(Symbol(), PERIOD_CURRENT, SlowMA, 0, MODE_SMA, PRICE_CLOSE, 1);

    double currentBid = SymbolInfoDouble(Symbol(), SYMBOL_BID);
    double currentAsk = SymbolInfoDouble(Symbol(), SYMBOL_ASK);
    double point = SymbolInfoDouble(Symbol(), SYMBOL_POINT);

    // BUY Signal: Fast MA crosses above Slow MA
    if(fastMA_Previous <= slowMA_Previous && fastMA_Current > slowMA_Current && !IsPositionOpen(POSITION_TYPE_BUY))
    {
        double volume = CalculateLotSize(StopLossPoints);
        if(volume <= 0) return;

        double sl = currentBid - (StopLossPoints * point);
        double tp = currentBid + (TakeProfitPoints * point);

        PlaceTrade(ORDER_TYPE_BUY, volume, sl, tp);
    }

    // SELL Signal: Fast MA crosses below Slow MA
    else if(fastMA_Previous >= slowMA_Previous && fastMA_Current < slowMA_Current && !IsPositionOpen(POSITION_TYPE_SELL))
    {
        double volume = CalculateLotSize(StopLossPoints);
        if(volume <= 0) return;

        double sl = currentAsk + (StopLossPoints * point);
        double tp = currentAsk - (TakeProfitPoints * point);

        PlaceTrade(ORDER_TYPE_SELL, volume, sl, tp);
    }
}

//+------------------------------------------------------------------+
//| Calculate lot size based on risk                                 |
//+------------------------------------------------------------------+
double CalculateLotSize(double stopLossPoints)
{
    double accountBalance = AccountInfoDouble(ACCOUNT_BALANCE);
    double riskAmount = accountBalance * (RiskPercent / 100.0);
    double tickValue = SymbolInfoDouble(Symbol(), SYMBOL_TRADE_TICK_VALUE);

    if(stopLossPoints <= 0 || tickValue <= 0)
    {
        Print("Invalid stop loss or tick value; cannot calculate lot size.");
        return(0);
    }

    double lotSize = riskAmount / (stopLossPoints * tickValue);
    double minLot = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_MIN);
    double maxLot = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_MAX);
    double stepLot = SymbolInfoDouble(Symbol(), SYMBOL_VOLUME_STEP);

    if(lotSize < minLot) lotSize = minLot;
    if(lotSize > maxLot) lotSize = maxLot;

    return(NormalizeDouble(MathMax(minLot, lotSize - fmod(lotSize - minLot, stepLot)), 2));
}

//+------------------------------------------------------------------+
//| Check if position is already open for symbol and type            |
//+------------------------------------------------------------------+
bool IsPositionOpen(ENUM_POSITION_TYPE type)
{
    for(int i = PositionsTotal() - 1; i >= 0; i--)
    {
        ulong ticket = PositionGetTicket(i);
        if(PositionGetString(POSITION_SYMBOL) == Symbol() && PositionGetInteger(POSITION_TYPE) == type)
            return(true);
    }
    return(false);
}

//+------------------------------------------------------------------+
//| Place trade order                                                |
//+------------------------------------------------------------------+
void PlaceTrade(ENUM_ORDER_TYPE orderType, double volume, double sl, double tp)
{
    CTrade trade;
    if(orderType == ORDER_TYPE_BUY)
        trade.Buy(volume, Symbol(), sl, tp);
    else if(orderType == ORDER_TYPE_SELL)
        trade.Sell(volume, Symbol(), sl, tp);

    if(!trade.ResultRetcode())
        Print("Trade failed: ", trade.ResultDescription());
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
}