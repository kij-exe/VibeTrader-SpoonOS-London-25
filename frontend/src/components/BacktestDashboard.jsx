import React, { useState, useEffect, useRef, useCallback } from 'react';
import { X, TrendingUp, TrendingDown, Loader2, ChevronDown } from 'lucide-react';

// Top 10 crypto pairs
const CRYPTO_PAIRS = [
  'BTCUSDT',
  'ETHUSDT',
  'SOLUSDT',
  'BNBUSDT',
  'XRPUSDT',
  'ADAUSDT',
  'DOGEUSDT',
  'AVAXUSDT',
  'DOTUSDT',
  'MATICUSDT',
];

const TIMEFRAMES = ['1m', '1h', '1d'];

// Animated Equity Chart Component
const EquityChart = ({ equityData, isLoading, isAnimating }) => {
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const [displayedPoints, setDisplayedPoints] = useState(0);

  // Animate the chart drawing
  useEffect(() => {
    if (!equityData || equityData.length === 0 || !isAnimating) {
      setDisplayedPoints(equityData?.length || 0);
      return;
    }

    setDisplayedPoints(0);
    let currentPoint = 0;
    const animationSpeed = Math.max(5, Math.floor(2000 / equityData.length)); // Complete in ~2 seconds

    const animate = () => {
      if (currentPoint < equityData.length) {
        currentPoint += 1;
        setDisplayedPoints(currentPoint);
        animationRef.current = setTimeout(animate, animationSpeed);
      }
    };

    animate();

    return () => {
      if (animationRef.current) {
        clearTimeout(animationRef.current);
      }
    };
  }, [equityData, isAnimating]);

  // Draw the chart
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !equityData || equityData.length === 0) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();

    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const width = rect.width;
    const height = rect.height;
    const padding = { top: 20, right: 20, bottom: 40, left: 70 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    // Get data to display
    const dataToShow = equityData.slice(0, displayedPoints);
    if (dataToShow.length === 0) return;

    // Calculate min/max for scaling - filter out NaN values
    const validValues = dataToShow.map(d => d.equity).filter(v => !isNaN(v) && isFinite(v));
    if (validValues.length === 0) return;
    
    const minValue = Math.min(...validValues) * 0.995;
    const maxValue = Math.max(...validValues) * 1.005;
    const valueRange = (maxValue - minValue) || 1;

    // Helper functions - use dataToShow.length for proper scaling
    const totalPoints = Math.max(dataToShow.length - 1, 1);
    const getX = (index) => padding.left + (index / totalPoints) * chartWidth;
    const getY = (value) => {
      if (isNaN(value) || !isFinite(value)) return padding.top + chartHeight / 2;
      return padding.top + chartHeight - ((value - minValue) / valueRange) * chartHeight;
    };

    // Draw grid lines
    ctx.strokeStyle = 'rgba(44, 255, 5, 0.1)';
    ctx.lineWidth = 1;

    // Horizontal grid lines
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (i / 5) * chartHeight;
      ctx.beginPath();
      ctx.moveTo(padding.left, y);
      ctx.lineTo(width - padding.right, y);
      ctx.stroke();

      // Y-axis labels
      const value = maxValue - (i / 5) * valueRange;
      ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
      ctx.font = '11px Inter, sans-serif';
      ctx.textAlign = 'right';
      if (!isNaN(value) && isFinite(value)) {
        ctx.fillText(`$${value.toLocaleString('en-US', { maximumFractionDigits: 0 })}`, padding.left - 10, y + 4);
      }
    }

    // Draw gradient fill under the line
    if (dataToShow.length > 1) {
      const gradient = ctx.createLinearGradient(0, padding.top, 0, height - padding.bottom);
      gradient.addColorStop(0, 'rgba(44, 255, 5, 0.3)');
      gradient.addColorStop(1, 'rgba(44, 255, 5, 0)');

      ctx.beginPath();
      ctx.moveTo(getX(0), height - padding.bottom);
      dataToShow.forEach((point, i) => {
        ctx.lineTo(getX(i), getY(point.equity));
      });
      ctx.lineTo(getX(dataToShow.length - 1), height - padding.bottom);
      ctx.closePath();
      ctx.fillStyle = gradient;
      ctx.fill();
    }

    // Draw the line
    if (dataToShow.length > 1) {
      ctx.beginPath();
      ctx.strokeStyle = '#2cff05';
      ctx.lineWidth = 2;
      ctx.lineCap = 'round';
      ctx.lineJoin = 'round';

      dataToShow.forEach((point, i) => {
        if (i === 0) {
          ctx.moveTo(getX(i), getY(point.equity));
        } else {
          ctx.lineTo(getX(i), getY(point.equity));
        }
      });
      ctx.stroke();

      // Glow effect
      ctx.shadowColor = '#2cff05';
      ctx.shadowBlur = 10;
      ctx.stroke();
      ctx.shadowBlur = 0;
    }

    // Draw current point indicator
    if (dataToShow.length > 0) {
      const lastPoint = dataToShow[dataToShow.length - 1];
      const x = getX(dataToShow.length - 1);
      const y = getY(lastPoint.equity);

      // Outer glow
      ctx.beginPath();
      ctx.arc(x, y, 8, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(44, 255, 5, 0.3)';
      ctx.fill();

      // Inner dot
      ctx.beginPath();
      ctx.arc(x, y, 4, 0, Math.PI * 2);
      ctx.fillStyle = '#2cff05';
      ctx.fill();
    }

    // X-axis labels (time)
    if (dataToShow.length > 0) {
      ctx.fillStyle = 'rgba(255, 255, 255, 0.5)';
      ctx.font = '10px Inter, sans-serif';
      ctx.textAlign = 'center';

      const labelCount = Math.min(6, dataToShow.length);
      for (let i = 0; i < labelCount; i++) {
        const dataIndex = Math.floor((i / (labelCount - 1)) * (dataToShow.length - 1));
        const point = dataToShow[dataIndex];
        if (point && point.time) {
          const x = getX(dataIndex);
          const date = new Date(point.time);
          const label = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
          ctx.fillText(label, x, height - padding.bottom + 20);
        }
      }
    }
  }, [equityData, displayedPoints]);

  if (isLoading) {
    return (
      <div className="h-64 flex flex-col items-center justify-center glass-card rounded-2xl">
        <div className="flex items-center gap-3 text-neon-400 mb-2">
          <Loader2 className="w-6 h-6 animate-spin" />
          <span>Running backtest...</span>
        </div>
        <span className="text-xs text-dark-400">This may take 1-3 minutes for minute data</span>
      </div>
    );
  }

  if (!equityData || equityData.length === 0) {
    return (
      <div className="h-64 flex flex-col items-center justify-center glass-card rounded-2xl">
        <span className="text-dark-400 mb-2">No trades executed</span>
        <span className="text-xs text-dark-500">Strategy conditions were not met during the backtest period</span>
      </div>
    );
  }

  return (
    <div className="relative">
      <canvas
        ref={canvasRef}
        className="w-full h-64 glass-card rounded-2xl"
        style={{ display: 'block' }}
      />
      {displayedPoints < equityData.length && (
        <div className="absolute bottom-4 right-4 text-xs text-neon-400 flex items-center gap-2">
          <div className="w-2 h-2 bg-neon-400 rounded-full animate-pulse" />
          Building chart...
        </div>
      )}
    </div>
  );
};

// Main Dashboard Component
const BacktestDashboard = ({ initialData, onClose }) => {
  const [selectedPair, setSelectedPair] = useState(initialData?.symbol || 'BTCUSDT');
  const [selectedTimeframe, setSelectedTimeframe] = useState(initialData?.timeframe || '1h');
  const [isPairDropdownOpen, setIsPairDropdownOpen] = useState(false);
  
  // Backtest results for each timeframe
  const [backtestResults, setBacktestResults] = useState({
    '1m': { loading: false, data: null, equityCurve: [], error: null },
    '1h': { loading: false, data: null, equityCurve: [], error: null },
    '1d': { loading: false, data: null, equityCurve: [], error: null },
  });

  const [isAnimating, setIsAnimating] = useState({});
  
  // Track which timeframes have been requested to prevent duplicates
  const requestedTimeframes = useRef(new Set());

  // Generate equity curve from backtest data using profitLoss
  const generateEquityCurve = useCallback((backtestData, initialCapital = 100000) => {
    if (!backtestData) {
      console.log('generateEquityCurve: No backtest data');
      return [];
    }

    console.log('generateEquityCurve: Processing data, keys:', Object.keys(backtestData));

    // Method 1: Use profitLoss object (most reliable for Lean results)
    // profitLoss contains { "2025-01-14T10:00:00Z": -1022.95, ... } for each closed trade
    if (backtestData.profitLoss && Object.keys(backtestData.profitLoss).length > 0) {
      console.log('Using profitLoss method');
      const profitLoss = backtestData.profitLoss;
      
      // Sort entries by timestamp
      const sortedEntries = Object.entries(profitLoss)
        .map(([time, pnl]) => ({ time, pnl: parseFloat(pnl) }))
        .sort((a, b) => new Date(a.time) - new Date(b.time));
      
      // Build equity curve by accumulating P&L
      let equity = initialCapital;
      const equityCurve = [{ 
        time: sortedEntries[0]?.time || new Date().toISOString(), 
        equity: initialCapital 
      }];
      
      sortedEntries.forEach(({ time, pnl }) => {
        equity += pnl;
        equityCurve.push({ time, equity });
      });
      
      console.log('Generated equity curve from profitLoss:', equityCurve.length, 'points');
      return equityCurve;
    }

    // Method 2: Try to use the charts data if available
    if (backtestData.charts && backtestData.charts['Strategy Equity']) {
      console.log('Using charts method');
      const equityChart = backtestData.charts['Strategy Equity'];
      if (equityChart.series && equityChart.series['Equity']) {
        const equitySeries = equityChart.series['Equity'];
        if (equitySeries.values && Object.keys(equitySeries.values).length > 0) {
          const values = equitySeries.values;
          const curve = Object.entries(values)
            .map(([timestamp, value]) => ({
              time: new Date(parseInt(timestamp) * 1000).toISOString(),
              equity: value.y !== undefined ? value.y : parseFloat(value),
            }))
            .filter(p => !isNaN(p.equity))
            .sort((a, b) => new Date(a.time) - new Date(b.time));
          
          console.log('Generated equity curve from charts:', curve.length, 'points');
          return curve;
        }
      }
    }

    // Method 3: Fallback - Generate from orders
    if (backtestData.orders && Object.keys(backtestData.orders).length > 0) {
      console.log('Using orders method');
      const orders = Object.values(backtestData.orders)
        .sort((a, b) => new Date(a.time) - new Date(b.time));

      if (orders.length === 0) return [];

      let equity = initialCapital;
      const equityCurve = [{ time: orders[0]?.time, equity: initialCapital }];
      let position = null;

      orders.forEach((order) => {
        const isBuy = order.direction === 0;
        const price = parseFloat(order.price);
        const quantity = Math.abs(parseFloat(order.quantity));

        if (isBuy && !position) {
          position = { entryPrice: price, quantity };
        } else if (!isBuy && position) {
          const pnl = (price - position.entryPrice) * position.quantity;
          equity += pnl;
          position = null;
        }

        equityCurve.push({ time: order.time, equity });
      });

      console.log('Generated equity curve from orders:', equityCurve.length, 'points');
      return equityCurve;
    }

    console.log('generateEquityCurve: No valid data source found');
    return [];
  }, []);

  // Initialize with provided data
  useEffect(() => {
    if (initialData?.backtestData) {
      console.log('BacktestDashboard: Initializing with data');
      console.log('  Symbol:', initialData.symbol);
      console.log('  Timeframe:', initialData.timeframe);
      console.log('  Backtest data keys:', Object.keys(initialData.backtestData));
      console.log('  profitLoss entries:', Object.keys(initialData.backtestData.profitLoss || {}).length);
      
      const timeframe = initialData.timeframe || '1h';
      const equityCurve = generateEquityCurve(initialData.backtestData, initialData.initialCapital || 100000);
      
      console.log('  Generated equity curve:', equityCurve.length, 'points');
      if (equityCurve.length > 0) {
        console.log('  First point:', equityCurve[0]);
        console.log('  Last point:', equityCurve[equityCurve.length - 1]);
      }
      
      // Mark this timeframe as already loaded (don't re-request it)
      requestedTimeframes.current.add(timeframe);
      
      setBacktestResults(prev => ({
        ...prev,
        [timeframe]: {
          loading: false,
          data: initialData.backtestData,
          equityCurve,
          error: null,
        }
      }));
      
      setIsAnimating(prev => ({ ...prev, [timeframe]: true }));
      
      // Reset animation flag after animation completes
      setTimeout(() => {
        setIsAnimating(prev => ({ ...prev, [timeframe]: false }));
      }, 3000);
    }
  }, [initialData, generateEquityCurve]);

  // Run backtest for all timeframes when pair changes
  const runBacktestsForPair = useCallback(async (pair) => {
    const strategyPath = initialData?.strategyPath;
    if (!strategyPath) {
      console.error('No strategy path available');
      return;
    }
    
    // Set all timeframes to loading
    setBacktestResults({
      '1m': { loading: true, data: null, equityCurve: [], error: null },
      '1h': { loading: true, data: null, equityCurve: [], error: null },
      '1d': { loading: true, data: null, equityCurve: [], error: null },
    });

    // Run backtests for each timeframe using REST API
    for (const tf of TIMEFRAMES) {
      try {
        console.log(`Running backtest for ${pair} ${tf}...`);
        
        const response = await fetch(`http://localhost:8000/api/backtest?symbol=${pair}&timeframe=${tf}&strategy_path=${encodeURIComponent(strategyPath)}`, {
          method: 'POST',
        });
        
        const data = await response.json();
        console.log(`Backtest result for ${tf}:`, data);
        
        if (!data.success) {
          throw new Error(data.error || 'Backtest failed');
        }
        
        // Log key metrics from received data
        if (data.backtest_data) {
          const bd = data.backtest_data;
          console.log(`[${tf}] Received backtest data:`);
          console.log(`  - profitLoss entries: ${Object.keys(bd.profitLoss || {}).length}`);
          console.log(`  - orders: ${Object.keys(bd.orders || {}).length}`);
          console.log(`  - runtimeStatistics:`, bd.runtimeStatistics);
          console.log(`  - totalPerformance.tradeStatistics.totalNumberOfTrades:`, 
            bd.totalPerformance?.tradeStatistics?.totalNumberOfTrades);
          
          const equityValues = bd.charts?.['Strategy Equity']?.series?.Equity?.values;
          console.log(`  - Equity chart values: ${Array.isArray(equityValues) ? equityValues.length : Object.keys(equityValues || {}).length}`);
        }
        
        const equityCurve = generateEquityCurve(data.backtest_data, 100000);
        console.log(`Equity curve for ${tf}: ${equityCurve.length} points`);
        
        setBacktestResults(prev => ({
          ...prev,
          [tf]: {
            loading: false,
            data: data.backtest_data,
            equityCurve,
            error: null,
          }
        }));
        
        if (equityCurve.length > 0) {
          setIsAnimating(prev => ({ ...prev, [tf]: true }));
          setTimeout(() => {
            setIsAnimating(prev => ({ ...prev, [tf]: false }));
          }, 3000);
        }
      } catch (error) {
        console.error(`Backtest error for ${tf}:`, error);
        setBacktestResults(prev => ({
          ...prev,
          [tf]: {
            loading: false,
            data: null,
            equityCurve: [],
            error: error.message,
          }
        }));
      }
    }
  }, [generateEquityCurve, initialData?.strategyPath]);

  // Handle pair change
  const handlePairChange = (pair) => {
    setSelectedPair(pair);
    setIsPairDropdownOpen(false);
    // Reset requested timeframes tracking for new pair
    requestedTimeframes.current.clear();
    runBacktestsForPair(pair);
  };

  // Run backtest for a single timeframe using REST API
  const runBacktestForTimeframe = useCallback(async (tf) => {
    // Set this timeframe to loading
    setBacktestResults(prev => ({
      ...prev,
      [tf]: { loading: true, data: null, equityCurve: [], error: null },
    }));

    try {
      // Get strategy path from initial data
      const strategyPath = initialData?.strategyPath;
      
      if (!strategyPath) {
        throw new Error('No strategy path available');
      }
      
      console.log(`Running backtest for ${selectedPair} ${tf}...`);
      
      // Simple REST call - backend runs Docker and reads local file
      const response = await fetch(`http://localhost:8000/api/backtest?symbol=${selectedPair}&timeframe=${tf}&strategy_path=${encodeURIComponent(strategyPath)}`, {
        method: 'POST',
      });
      
      const data = await response.json();
      console.log(`Backtest result for ${tf}:`, data);
      
      if (!data.success) {
        throw new Error(data.error || 'Backtest failed');
      }
      
      const equityCurve = generateEquityCurve(data.backtest_data, 100000);
      console.log(`Equity curve for ${tf}:`, equityCurve.length, 'points');
      
      setBacktestResults(prev => ({
        ...prev,
        [tf]: {
          loading: false,
          data: data.backtest_data,
          equityCurve,
          error: null,
        }
      }));
      
      if (equityCurve.length > 0) {
        setIsAnimating(prev => ({ ...prev, [tf]: true }));
        setTimeout(() => {
          setIsAnimating(prev => ({ ...prev, [tf]: false }));
        }, 3000);
      }
    } catch (error) {
      console.error(`Backtest error for ${tf}:`, error);
      setBacktestResults(prev => ({
        ...prev,
        [tf]: {
          loading: false,
          data: null,
          equityCurve: [],
          error: error.message,
        }
      }));
    }
  }, [selectedPair, generateEquityCurve, initialData?.strategyPath]);

  // Handle timeframe change - run backtest if no data or retry on error
  const handleTimeframeChange = (tf) => {
    setSelectedTimeframe(tf);
    
    const tfData = backtestResults[tf];
    
    // If there's an error, allow retry
    if (tfData.error && !tfData.loading) {
      requestedTimeframes.current.delete(tf);
      requestedTimeframes.current.add(tf);
      runBacktestForTimeframe(tf);
      return;
    }
    
    // If this timeframe has no data, is not loading, and hasn't been requested yet
    if (!tfData.data && !tfData.loading && !requestedTimeframes.current.has(tf)) {
      requestedTimeframes.current.add(tf);
      runBacktestForTimeframe(tf);
    }
  };

  // Get current timeframe data
  const currentData = backtestResults[selectedTimeframe];

  // Calculate metrics from backtest data
  const getMetrics = (data) => {
    if (!data || !data.data) {
      return {
        totalReturn: 0,
        maxDrawdown: 0,
        winRate: 0,
        totalTrades: 0,
        sharpeRatio: 0,
      };
    }

    const backtestData = data.data;
    
    // Try different locations for statistics
    const stats = backtestData.total_performance_statistics || 
                  backtestData.statistics || 
                  backtestData.TotalPerformance?.PortfolioStatistics ||
                  {};
    
    // Count orders/trades - Lean uses "Total Orders" which is buy+sell, so divide by 2 for round trips
    const orderCount = backtestData.orders ? Object.keys(backtestData.orders).length : 0;
    const totalOrders = parseInt(stats['Total Orders'] || stats['Total Trades'] || stats['TotalTrades'] || orderCount || 0);
    const totalTrades = Math.floor(totalOrders / 2); // Each trade is a buy + sell
    
    // Get return - try multiple formats (prefer Net Profit over Compounding Annual Return)
    let totalReturn = 0;
    if (stats['Net Profit']) {
      // Lean format: "35.960%"
      const val = stats['Net Profit'];
      totalReturn = typeof val === 'string' ? parseFloat(val.replace('%', '')) : parseFloat(val) * 100;
    } else if (stats['Total Net Profit']) {
      const val = stats['Total Net Profit'];
      totalReturn = typeof val === 'string' ? parseFloat(val.replace('%', '')) : parseFloat(val) * 100;
    } else if (stats['Compounding Annual Return']) {
      const val = stats['Compounding Annual Return'];
      totalReturn = typeof val === 'string' ? parseFloat(val.replace('%', '')) : parseFloat(val) * 100;
    }
    
    // Get drawdown
    let maxDrawdown = 0;
    if (stats['Drawdown']) {
      const val = stats['Drawdown'];
      maxDrawdown = typeof val === 'string' ? parseFloat(val.replace('%', '')) : parseFloat(val) * 100;
    }
    
    // Get win rate
    let winRate = 0;
    if (stats['Win Rate']) {
      const val = stats['Win Rate'];
      winRate = typeof val === 'string' ? parseFloat(val.replace('%', '')) : parseFloat(val) * 100;
    }
    
    // Get Sharpe ratio
    let sharpeRatio = 0;
    if (stats['Sharpe Ratio']) {
      sharpeRatio = parseFloat(stats['Sharpe Ratio']);
    }
    
    return {
      totalReturn,
      maxDrawdown,
      winRate,
      totalTrades,
      sharpeRatio,
    };
  };

  const metrics = getMetrics(currentData);

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-50 flex items-center justify-center p-4">
      {/* Background effects */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute w-96 h-96 rounded-full bg-neon-400/10 blur-[120px] -top-20 -left-20" />
        <div className="absolute w-80 h-80 rounded-full bg-neon-400/10 blur-[100px] -bottom-20 -right-20" />
      </div>

      <div className="glass-card rounded-3xl max-w-5xl w-full max-h-[90vh] overflow-hidden flex flex-col relative neon-border">
        {/* Header with Pair Selection and Timeframes */}
        <div className="flex items-center justify-between p-5 border-b border-neon-400/10 glass-strong" style={{ zIndex: isPairDropdownOpen ? 99999 : 10, position: 'relative' }}>
          <div className="flex items-center gap-6">
            {/* Pair Dropdown */}
            <div className="relative" style={{ zIndex: isPairDropdownOpen ? 9999 : 'auto' }}>
              <button
                onClick={() => setIsPairDropdownOpen(!isPairDropdownOpen)}
                className="flex items-center gap-2 px-4 py-2.5 glass-card rounded-xl hover:border-neon-400/30 transition-all"
              >
                <span className="text-white font-semibold">{selectedPair}</span>
                <ChevronDown className={`w-4 h-4 text-dark-400 transition-transform ${isPairDropdownOpen ? 'rotate-180' : ''}`} />
              </button>
              
              {isPairDropdownOpen && (
                <div 
                  className="absolute top-full left-0 mt-2 w-48 rounded-xl border border-neon-400/30 overflow-hidden shadow-2xl max-h-80 overflow-y-auto"
                  style={{ backgroundColor: '#0a0f0a' }}
                >
                  {CRYPTO_PAIRS.map((pair) => (
                    <button
                      key={pair}
                      onClick={() => handlePairChange(pair)}
                      className={`w-full px-4 py-2.5 text-left text-sm transition-colors ${
                        pair === selectedPair ? 'text-neon-400' : 'text-white hover:bg-white/10'
                      }`}
                      style={{ backgroundColor: pair === selectedPair ? 'rgba(0, 255, 136, 0.15)' : '#0a0f0a' }}
                    >
                      {pair}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Timeframe Tabs - TradingView style */}
            <div className="flex items-center gap-1 p-1 glass rounded-xl">
              {TIMEFRAMES.map((tf) => (
                <button
                  key={tf}
                  onClick={() => handleTimeframeChange(tf)}
                  className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    tf === selectedTimeframe
                      ? 'bg-neon-400 text-black'
                      : 'text-dark-300 hover:text-white hover:bg-white/5'
                  }`}
                >
                  {tf}
                  {backtestResults[tf].loading && (
                    <Loader2 className="w-3 h-3 ml-1 inline animate-spin" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* Close Button */}
          <button
            onClick={onClose}
            className="p-2.5 glass hover:bg-neon-400/10 rounded-xl transition-all"
          >
            <X className="w-5 h-5 text-dark-300 hover:text-neon-400" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-5 space-y-5">
          {/* Metrics Row */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
            <MetricCard
              label="Total Return"
              value={`${metrics.totalReturn >= 0 ? '+' : ''}${metrics.totalReturn.toFixed(2)}%`}
              isPositive={metrics.totalReturn >= 0}
              isNegative={metrics.totalReturn < 0}
            />
            <MetricCard
              label="Max Drawdown"
              value={`${metrics.maxDrawdown.toFixed(2)}%`}
              isNegative={true}
            />
            <MetricCard
              label="Win Rate"
              value={`${metrics.winRate.toFixed(1)}%`}
              isPositive={metrics.winRate >= 50}
            />
            <MetricCard
              label="Total Trades"
              value={metrics.totalTrades.toString()}
            />
            <MetricCard
              label="Sharpe Ratio"
              value={metrics.sharpeRatio.toFixed(2)}
              isPositive={metrics.sharpeRatio >= 1}
            />
          </div>

          {/* Equity Chart */}
          <div>
            <h3 className="text-sm font-semibold text-dark-200 mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-neon-400" />
              Equity Curve - {selectedPair} ({selectedTimeframe})
            </h3>
            <EquityChart
              equityData={currentData.equityCurve}
              isLoading={currentData.loading}
              isAnimating={isAnimating[selectedTimeframe]}
            />
          </div>

          {/* Error Display */}
          {currentData.error && (
            <div className="glass-card rounded-xl p-4 border border-red-500/30 flex items-center justify-between">
              <p className="text-red-400 text-sm">{currentData.error}</p>
              <button
                onClick={() => {
                  requestedTimeframes.current.delete(selectedTimeframe);
                  runBacktestForTimeframe(selectedTimeframe);
                }}
                className="px-3 py-1 text-xs bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-colors"
              >
                Retry
              </button>
            </div>
          )}

          {/* Timeframe Comparison */}
          <div className="glass-card rounded-2xl p-4">
            <h3 className="text-sm font-semibold text-dark-200 mb-4">Timeframe Comparison</h3>
            <div className="grid grid-cols-3 gap-4">
              {TIMEFRAMES.map((tf) => {
                const tfMetrics = getMetrics(backtestResults[tf]);
                const isSelected = tf === selectedTimeframe;
                const isLoading = backtestResults[tf].loading;
                
                const hasData = backtestResults[tf].data !== null;
                const hasError = backtestResults[tf].error !== null;
                
                return (
                  <button
                    key={tf}
                    onClick={() => handleTimeframeChange(tf)}
                    className={`p-4 rounded-xl transition-all ${
                      isSelected
                        ? 'glass-card neon-border'
                        : 'glass hover:border-neon-400/20'
                    }`}
                  >
                    <div className="text-lg font-bold text-white mb-2">{tf}</div>
                    {isLoading ? (
                      <Loader2 className="w-5 h-5 text-neon-400 animate-spin mx-auto" />
                    ) : hasError ? (
                      <div className="text-xs text-red-400">Error - click to retry</div>
                    ) : !hasData ? (
                      <div className="text-xs text-dark-400">Click to run backtest</div>
                    ) : tfMetrics.totalTrades === 0 ? (
                      <div className="text-xs text-dark-400">No trades</div>
                    ) : (
                      <>
                        <div className={`text-xl font-bold ${
                          tfMetrics.totalReturn >= 0 ? 'text-neon-400' : 'text-red-400'
                        }`}>
                          {tfMetrics.totalReturn >= 0 ? '+' : ''}{tfMetrics.totalReturn.toFixed(2)}%
                        </div>
                        <div className="text-xs text-dark-400 mt-1">
                          {tfMetrics.totalTrades} trades
                        </div>
                      </>
                    )}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// Metric Card Component
const MetricCard = ({ label, value, isPositive, isNegative }) => {
  return (
    <div className="glass-card rounded-xl p-3">
      <p className="text-xs text-dark-400 mb-1">{label}</p>
      <p className={`text-lg font-bold ${
        isPositive ? 'text-neon-400' : isNegative ? 'text-red-400' : 'text-white'
      }`}>
        {value}
      </p>
    </div>
  );
};

export default BacktestDashboard;
