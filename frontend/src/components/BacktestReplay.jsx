import React, { useState, useEffect } from 'react';
import { X, Play, Pause, SkipForward, RotateCcw, TrendingUp, TrendingDown } from 'lucide-react';

const BacktestReplay = ({ backtestData, onClose, metadata }) => {
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentOrderIndex, setCurrentOrderIndex] = useState(0);
  const [speed, setSpeed] = useState(100); // ms per order
  const [runningMetrics, setRunningMetrics] = useState({
    equity: metadata?.initialCapital || 100000,
    totalTrades: 0,
    winningTrades: 0,
    losingTrades: 0,
    winRate: 0,
    totalPnL: 0,
    maxDrawdown: 0,
    currentDrawdown: 0,
    peakEquity: metadata?.initialCapital || 100000,
    returnPercent: 0,
  });

  // Extract orders from backtest data
  const orders = React.useMemo(() => {
    if (!backtestData || !backtestData.orders) return [];
    
    return Object.values(backtestData.orders)
      .sort((a, b) => new Date(a.time) - new Date(b.time));
  }, [backtestData]);

  // Process orders up to current index
  useEffect(() => {
    if (orders.length === 0) return;
    
    const processedOrders = orders.slice(0, currentOrderIndex + 1);
    const initialCapital = metadata?.initialCapital || 100000;
    
    let equity = initialCapital;
    let peakEquity = initialCapital;
    let totalPnL = 0;
    let maxDrawdown = 0;
    
    // Track positions
    const positions = {}; // symbol -> {quantity, entryPrice, entryValue}
    let closedTrades = [];
    
    processedOrders.forEach((order) => {
      const symbol = order.symbol?.value || order.symbol?.permtick || 'UNKNOWN';
      const isBuy = order.direction === 0; // 0 = Buy, 1 = Sell
      const quantity = Math.abs(order.quantity);
      const price = order.price;
      const value = Math.abs(order.value);
      
      if (!positions[symbol]) {
        positions[symbol] = { quantity: 0, entryPrice: 0, entryValue: 0 };
      }
      
      if (isBuy) {
        // Opening or adding to position
        positions[symbol].quantity += quantity;
        positions[symbol].entryValue += value;
        positions[symbol].entryPrice = positions[symbol].entryValue / positions[symbol].quantity;
      } else {
        // Closing or reducing position
        if (positions[symbol].quantity > 0) {
          const exitValue = value;
          const exitQuantity = quantity;
          const entryPrice = positions[symbol].entryPrice;
          const exitPrice = price;
          
          // Calculate P&L for this trade
          const tradePnL = exitValue - (entryPrice * exitQuantity);
          totalPnL += tradePnL;
          equity += tradePnL;
          
          // Track trade
          closedTrades.push({
            symbol,
            pnl: tradePnL,
            isWin: tradePnL > 0,
          });
          
          // Update position
          positions[symbol].quantity -= exitQuantity;
          if (positions[symbol].quantity <= 0) {
            positions[symbol] = { quantity: 0, entryPrice: 0, entryValue: 0 };
          } else {
            positions[symbol].entryValue = positions[symbol].entryPrice * positions[symbol].quantity;
          }
        }
      }
      
      // Update peak and drawdown
      if (equity > peakEquity) {
        peakEquity = equity;
      }
      
      const currentDrawdown = ((equity - peakEquity) / peakEquity) * 100;
      if (currentDrawdown < maxDrawdown) {
        maxDrawdown = currentDrawdown;
      }
    });
    
    const winningTrades = closedTrades.filter(t => t.isWin).length;
    const losingTrades = closedTrades.filter(t => !t.isWin).length;
    const winRate = closedTrades.length > 0 ? (winningTrades / closedTrades.length) * 100 : 0;
    
    setRunningMetrics({
      equity: equity,
      totalTrades: closedTrades.length,
      winningTrades,
      losingTrades,
      winRate,
      totalPnL,
      maxDrawdown,
      currentDrawdown: ((equity - peakEquity) / peakEquity) * 100,
      peakEquity,
      returnPercent: ((equity - initialCapital) / initialCapital) * 100,
    });
  }, [currentOrderIndex, orders, metadata]);

  // Auto-play logic
  useEffect(() => {
    if (!isPlaying || currentOrderIndex >= orders.length - 1) {
      if (currentOrderIndex >= orders.length - 1) {
        setIsPlaying(false);
      }
      return;
    }
    
    const timer = setTimeout(() => {
      setCurrentOrderIndex(prev => Math.min(prev + 1, orders.length - 1));
    }, speed);
    
    return () => clearTimeout(timer);
  }, [isPlaying, currentOrderIndex, orders.length, speed]);

  const handlePlayPause = () => {
    if (currentOrderIndex >= orders.length - 1) {
      setCurrentOrderIndex(0);
      setIsPlaying(true);
    } else {
      setIsPlaying(!isPlaying);
    }
  };

  const handleReset = () => {
    setCurrentOrderIndex(0);
    setIsPlaying(false);
  };

  const handleSkip = () => {
    if (currentOrderIndex < orders.length - 1) {
      setCurrentOrderIndex(prev => Math.min(prev + 10, orders.length - 1));
    }
  };

  const currentOrder = orders[currentOrderIndex];
  const progress = orders.length > 0 ? ((currentOrderIndex + 1) / orders.length) * 100 : 0;

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-md z-50 flex items-center justify-center p-4">
      {/* Floating orbs for modal background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute w-96 h-96 rounded-full bg-neon-400/20 blur-[100px] -top-20 -left-20 animate-pulse" />
        <div className="absolute w-80 h-80 rounded-full bg-neon-400/15 blur-[80px] -bottom-20 -right-20 animate-pulse" style={{ animationDelay: '1s' }} />
      </div>
      
      <div className="glass-card rounded-3xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col relative neon-border">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-neon-400/10 glass-strong">
          <div>
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <span className="text-2xl">📊</span>
              <span>Backtest Order Replay</span>
            </h2>
            <p className="text-sm text-dark-300 mt-1">
              {metadata?.symbol} • {metadata?.timeframe} • {orders.length} orders
            </p>
          </div>
          <button
            onClick={onClose}
            className="p-2.5 glass hover:bg-neon-400/10 rounded-xl transition-all hover:neon-border"
          >
            <X className="w-5 h-5 text-dark-300 hover:text-neon-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6 space-y-6">
          {/* Metrics Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              label="Equity"
              value={`$${(runningMetrics.equity || 0).toFixed(2)}`}
              change={runningMetrics.returnPercent || 0}
              isPositive={(runningMetrics.returnPercent || 0) >= 0}
            />
            <MetricCard
              label="Total P&L"
              value={`${(runningMetrics.totalPnL || 0) >= 0 ? '+' : ''}$${(runningMetrics.totalPnL || 0).toFixed(2)}`}
              isPositive={(runningMetrics.totalPnL || 0) >= 0}
            />
            <MetricCard
              label="Win Rate"
              value={`${(runningMetrics.winRate || 0).toFixed(1)}%`}
              subValue={`${runningMetrics.winningTrades || 0}W / ${runningMetrics.losingTrades || 0}L`}
            />
            <MetricCard
              label="Max Drawdown"
              value={`${(runningMetrics.maxDrawdown || 0).toFixed(2)}%`}
              isNegative={(runningMetrics.maxDrawdown || 0) < 0}
            />
          </div>

          {/* Current Order */}
          {currentOrder && (
            <div className="glass-card rounded-2xl p-5">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-dark-200">
                  Order #{currentOrderIndex + 1} of {orders.length}
                </h3>
                <span className={`px-4 py-1.5 rounded-full text-xs font-semibold ${
                  currentOrder.direction === 0
                    ? 'bg-neon-400/20 text-neon-400 neon-border'
                    : 'bg-red-500/20 text-red-400 border border-red-500/30'
                }`}>
                  {currentOrder.direction === 0 ? 'BUY' : 'SELL'}
                </span>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-sm">
                <div>
                  <p className="text-dark-400 text-xs mb-1">Symbol</p>
                  <p className="text-white font-semibold">
                    {currentOrder.symbol?.value || currentOrder.symbol?.permtick}
                  </p>
                </div>
                <div>
                  <p className="text-dark-400 text-xs mb-1">Price</p>
                  <p className="text-white font-semibold">${(currentOrder.price || 0).toFixed(4)}</p>
                </div>
                <div>
                  <p className="text-dark-400 text-xs mb-1">Quantity</p>
                  <p className="text-white font-semibold">{Math.abs(currentOrder.quantity || 0).toFixed(2)}</p>
                </div>
                <div>
                  <p className="text-dark-400 text-xs mb-1">Time</p>
                  <p className="text-white font-semibold">
                    {new Date(currentOrder.time).toLocaleDateString()}
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Progress Bar */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm">
              <span className="text-dark-400">Progress</span>
              <span className="text-neon-400 font-medium">{progress.toFixed(1)}%</span>
            </div>
            <div className="w-full glass rounded-full h-2.5 overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-neon-400 to-neon-500 transition-all duration-300 rounded-full"
                style={{ width: `${progress}%`, boxShadow: '0 0 20px rgba(44, 255, 5, 0.5)' }}
              />
            </div>
          </div>

          {/* Trade Stats */}
          <div className="glass-card rounded-2xl p-5">
            <h3 className="text-sm font-semibold text-dark-200 mb-4">Trade Statistics</h3>
            <div className="grid grid-cols-3 gap-6 text-sm">
              <div>
                <p className="text-dark-400 text-xs mb-1">Total Trades</p>
                <p className="text-white font-bold text-2xl">{runningMetrics.totalTrades}</p>
              </div>
              <div>
                <p className="text-neon-400 text-xs mb-1">Winning</p>
                <p className="text-neon-400 font-bold text-2xl">{runningMetrics.winningTrades}</p>
              </div>
              <div>
                <p className="text-red-400 text-xs mb-1">Losing</p>
                <p className="text-red-400 font-bold text-2xl">{runningMetrics.losingTrades}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Controls */}
        <div className="p-6 border-t border-neon-400/10 glass-strong">
          <div className="flex items-center justify-center gap-4">
            <button
              onClick={handleReset}
              className="p-3 glass hover:bg-neon-400/10 rounded-xl transition-all group"
              title="Reset"
            >
              <RotateCcw className="w-5 h-5 text-dark-300 group-hover:text-neon-400 transition-colors" />
            </button>
            
            <button
              onClick={handlePlayPause}
              className="p-4 neon-btn rounded-xl transition-all neon-glow"
              title={isPlaying ? 'Pause' : 'Play'}
            >
              {isPlaying ? (
                <Pause className="w-6 h-6" />
              ) : (
                <Play className="w-6 h-6" />
              )}
            </button>
            
            <button
              onClick={handleSkip}
              className="p-3 glass hover:bg-neon-400/10 rounded-xl transition-all group"
              title="Skip +10"
            >
              <SkipForward className="w-5 h-5 text-dark-300 group-hover:text-neon-400 transition-colors" />
            </button>
          </div>
          
          {/* Speed Control */}
          <div className="mt-4 flex items-center justify-center gap-3">
            <span className="text-sm text-dark-400">Speed:</span>
            <select
              value={speed}
              onChange={(e) => setSpeed(Number(e.target.value))}
              className="glass-input text-white rounded-xl px-4 py-2 text-sm focus:outline-none focus:border-neon-400/40"
            >
              <option value={500}>0.5x</option>
              <option value={250}>1x</option>
              <option value={100}>2.5x</option>
              <option value={50}>5x</option>
              <option value={10}>10x</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  );
};

const MetricCard = ({ label, value, subValue, change, isPositive, isNegative }) => {
  return (
    <div className="glass-card rounded-xl p-4">
      <p className="text-xs text-dark-400 mb-1.5">{label}</p>
      <div className="flex items-baseline gap-2">
        <p className={`text-xl font-bold ${
          isPositive ? 'text-neon-400' : isNegative ? 'text-red-400' : 'text-white'
        }`}>
          {value}
        </p>
        {change !== undefined && (
          <span className={`flex items-center text-xs ${
            change >= 0 ? 'text-neon-400' : 'text-red-400'
          }`}>
            {change >= 0 ? <TrendingUp className="w-3 h-3 mr-1" /> : <TrendingDown className="w-3 h-3 mr-1" />}
            {Math.abs(change).toFixed(2)}%
          </span>
        )}
      </div>
      {subValue && <p className="text-xs text-dark-300 mt-1.5">{subValue}</p>}
    </div>
  );
};

export default BacktestReplay;
