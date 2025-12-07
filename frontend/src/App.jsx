import React, { useEffect, useRef, useState, useCallback } from 'react';
import { TrendingUp, Zap, Shield, BarChart3, Activity } from 'lucide-react';
import { useWebSocket } from './hooks/useWebSocket';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ConnectionStatus from './components/ConnectionStatus';

// Lava Lamp Orbs Background Component
const LavaLampOrbs = () => {
  const canvasRef = useRef(null);
  const animationFrameRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    let width = window.innerWidth;
    let height = window.innerHeight;

    // Setup canvas
    const setupCanvas = () => {
      const dpr = window.devicePixelRatio || 1;
      width = window.innerWidth;
      height = window.innerHeight;
      canvas.width = width * dpr;
      canvas.height = height * dpr;
      canvas.style.width = width + 'px';
      canvas.style.height = height + 'px';
      ctx.scale(dpr, dpr);
    };

    setupCanvas();
    window.addEventListener('resize', setupCanvas);

    // Orb class for lava lamp blobs
    class Orb {
      constructor(x, y, radius, speedX, speedY) {
        this.baseX = x;
        this.baseY = y;
        this.x = x;
        this.y = y;
        this.radius = radius;
        this.baseRadius = radius;
        this.speedX = speedX;
        this.speedY = speedY;
        this.angle = Math.random() * Math.PI * 2;
        this.angleSpeed = 0.002 + Math.random() * 0.003;
        this.wobbleX = Math.random() * Math.PI * 2;
        this.wobbleY = Math.random() * Math.PI * 2;
      }

      update(time) {
        this.angle += this.angleSpeed;
        this.wobbleX += 0.01;
        this.wobbleY += 0.013;
        
        // Organic movement pattern
        this.x = this.baseX + Math.sin(this.angle) * 150 + Math.sin(this.wobbleX) * 50;
        this.y = this.baseY + Math.cos(this.angle * 0.7) * 100 + Math.cos(this.wobbleY) * 40;
        
        // Pulsing radius
        this.radius = this.baseRadius + Math.sin(time * 0.001) * 20;
        
        // Keep within bounds with soft bounce
        if (this.x < this.radius) this.baseX += 2;
        if (this.x > width - this.radius) this.baseX -= 2;
        if (this.y < this.radius) this.baseY += 2;
        if (this.y > height - this.radius) this.baseY -= 2;
      }
    }

    // Create two orbs
    const orbs = [
      new Orb(width * 0.3, height * 0.4, 180, 0.5, 0.3),
      new Orb(width * 0.7, height * 0.6, 150, -0.4, -0.35),
    ];

    // Draw orbs with glow effect
    const drawOrbs = () => {
      for (const orb of orbs) {
        const gradient = ctx.createRadialGradient(
          orb.x, orb.y, 0,
          orb.x, orb.y, orb.radius * 1.5
        );
        gradient.addColorStop(0, 'rgba(44, 255, 5, 0.1)');
        gradient.addColorStop(0.4, 'rgba(44, 255, 5, 0.08)');
        gradient.addColorStop(0.7, 'rgba(44, 255, 5, 0.03)');
        gradient.addColorStop(1, 'rgba(44, 255, 5, 0)');
        ctx.fillStyle = gradient;
        ctx.beginPath();
        ctx.arc(orb.x, orb.y, orb.radius * 1.5, 0, Math.PI * 2);
        ctx.fill();
      }
    };

    // Animation loop
    const animate = (time) => {
      ctx.clearRect(0, 0, width, height);
      
      // Update orbs
      orbs.forEach(orb => orb.update(time));
      
      // Draw orbs
      drawOrbs();
      
      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('resize', setupCanvas);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 z-0 pointer-events-none"
      style={{ background: 'transparent' }}
    />
  );
};

// Interactive Grid Background Component
const GridBackground = () => {
  const canvasRef = useRef(null);
  const gridStateRef = useRef({
    cols: 0,
    rows: 0,
    cellSize: 35,
    hoveredCell: null,
    ripples: [], // Array of { centerRow, centerCol, currentRadius, startTime }
  });
  const animationFrameRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    const state = gridStateRef.current;

    // Setup canvas size
    const setupCanvas = () => {
      const dpr = window.devicePixelRatio || 1;
      canvas.width = window.innerWidth * dpr;
      canvas.height = window.innerHeight * dpr;
      canvas.style.width = window.innerWidth + 'px';
      canvas.style.height = window.innerHeight + 'px';
      ctx.scale(dpr, dpr);
      
      state.cols = Math.ceil(window.innerWidth / state.cellSize);
      state.rows = Math.ceil(window.innerHeight / state.cellSize);
    };

    setupCanvas();
    window.addEventListener('resize', setupCanvas);

    // Get cell from mouse position
    const getCellFromMouse = (e) => {
      const rect = canvas.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const col = Math.floor(x / state.cellSize);
      const row = Math.floor(y / state.cellSize);
      if (col >= 0 && col < state.cols && row >= 0 && row < state.rows) {
        return { row, col };
      }
      return null;
    };

    // Mouse move handler
    const handleMouseMove = (e) => {
      const cell = getCellFromMouse(e);
      state.hoveredCell = cell;
    };

    // Mouse leave handler
    const handleMouseLeave = () => {
      state.hoveredCell = null;
    };

    // Click handler - trigger ripple
    const handleClick = (e) => {
      const cell = getCellFromMouse(e);
      if (cell) {
        state.ripples.push({
          centerRow: cell.row,
          centerCol: cell.col,
          startTime: performance.now(),
        });
      }
    };

    // Draw function
    const draw = (timestamp) => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const { cols, rows, cellSize, hoveredCell, ripples } = state;

      // Process ripples and calculate cell intensities
      const cellIntensities = {};
      
      ripples.forEach((ripple, rippleIndex) => {
        const elapsed = timestamp - ripple.startTime;
        const currentRadius = Math.floor(elapsed / 50); // Speed of ripple expansion (integer for crisp rings)
        const maxRadius = cols + rows; // Manhattan distance max

        if (currentRadius > maxRadius) {
          // Mark for removal
          ripple.done = true;
          return;
        }

        // Calculate intensity for each cell based on Manhattan distance (diamond/rhombus pattern)
        for (let row = 0; row < rows; row++) {
          for (let col = 0; col < cols; col++) {
            // Manhattan distance creates diamond/rhombus shape
            const distance = Math.abs(row - ripple.centerRow) + Math.abs(col - ripple.centerCol);
            
            // Only light up cells exactly at the current radius (1 cell thick ring)
            if (distance === currentRadius) {
              const key = `${row}-${col}`;
              // Intensity decreases with distance from center (wave amplitude decay)
              const intensity = Math.max(0.1, 1 - (currentRadius / 25));
              cellIntensities[key] = Math.max(cellIntensities[key] || 0, intensity);
            }
          }
        }
      });

      // Remove completed ripples
      state.ripples = ripples.filter(r => !r.done);

      // Draw grid
      for (let row = 0; row < rows; row++) {
        for (let col = 0; col < cols; col++) {
          const x = col * cellSize;
          const y = row * cellSize;
          const key = `${row}-${col}`;
          
          let alpha = 0.03; // Base alpha
          let borderAlpha = 0.1;
          let glowSize = 0;

          // Check if hovered
          const isHovered = hoveredCell && hoveredCell.row === row && hoveredCell.col === col;
          
          // Check ripple intensity
          const rippleIntensity = cellIntensities[key] || 0;

          if (isHovered) {
            alpha = 0.7;
            borderAlpha = 1;
            glowSize = 0;
          } else if (rippleIntensity > 0) {
            alpha = 0.1 + rippleIntensity * 0.5;
            borderAlpha = 0.15 + rippleIntensity * 0.6;
            glowSize = rippleIntensity * 12;
          }

          // Draw glow
          if (glowSize > 0) {
            const gradient = ctx.createRadialGradient(
              x + cellSize / 2, y + cellSize / 2, 0,
              x + cellSize / 2, y + cellSize / 2, cellSize + glowSize
            );
            gradient.addColorStop(0, `rgba(44, 255, 5, ${alpha * 0.8})`);
            gradient.addColorStop(1, 'rgba(44, 255, 5, 0)');
            ctx.fillStyle = gradient;
            ctx.fillRect(x - glowSize, y - glowSize, cellSize + glowSize * 2, cellSize + glowSize * 2);
          }

          // Draw cell background
          ctx.fillStyle = `rgba(44, 255, 5, ${alpha})`;
          ctx.fillRect(x + 1, y + 1, cellSize - 2, cellSize - 2);

          // Draw cell border
          ctx.strokeStyle = `rgba(44, 255, 5, ${borderAlpha})`;
          ctx.lineWidth = 1;
          ctx.strokeRect(x + 0.5, y + 0.5, cellSize - 1, cellSize - 1);
        }
      }

      animationFrameRef.current = requestAnimationFrame(draw);
    };

    // Start animation loop
    animationFrameRef.current = requestAnimationFrame(draw);

    // Add event listeners to window (not canvas) to capture all events
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('click', handleClick);
    canvas.addEventListener('mouseleave', handleMouseLeave);

    return () => {
      window.removeEventListener('resize', setupCanvas);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('click', handleClick);
      canvas.removeEventListener('mouseleave', handleMouseLeave);
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
      }
    };
  }, []);

  return (
    <canvas
      ref={canvasRef}
      className="fixed inset-0 z-0 pointer-events-none"
      style={{ background: 'transparent' }}
    />
  );
};

function App() {
  const { isConnected, isReconnecting, messages, sendMessage, connect } = useWebSocket();
  const messagesEndRef = useRef(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSendMessage = (content) => {
    sendMessage(content);
  };

  return (
    <div className="h-screen bg-black flex overflow-hidden relative">
      {/* Lava Lamp Orbs Background */}
      <LavaLampOrbs />
      {/* Interactive Grid Background */}
      <GridBackground />

      {/* Sidebar */}
      <aside className="hidden lg:flex w-72 glass-strong flex-col z-10 border-r border-neon-400/10">
        {/* Logo */}
        <div className="p-6 border-b border-neon-400/10">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-neon-400/30 to-neon-600/20 flex items-center justify-center neon-border">
              <TrendingUp className="w-6 h-6 text-neon-400" />
            </div>
            <div>
              <h1 className="text-lg font-bold neon-text">VibeTrade</h1>
              <p className="text-xs text-dark-400">AI Portfolio Manager</p>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="flex-1 p-4">
          <h2 className="text-xs font-semibold text-dark-400 uppercase tracking-wider mb-4">
            Features
          </h2>
          <nav className="space-y-2">
            <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl glass-card text-neon-400">
              <Zap className="w-4 h-4" />
              <span className="text-sm font-medium">Strategy Builder</span>
            </div>
            <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-dark-400 hover:glass transition-all cursor-not-allowed">
              <BarChart3 className="w-4 h-4" />
              <span className="text-sm">Backtesting</span>
              <span className="text-xs bg-neon-400/10 text-neon-400/70 px-2 py-0.5 rounded-full ml-auto">Soon</span>
            </div>
            <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-dark-400 hover:glass transition-all cursor-not-allowed">
              <Shield className="w-4 h-4" />
              <span className="text-sm">Risk Analysis</span>
              <span className="text-xs bg-neon-400/10 text-neon-400/70 px-2 py-0.5 rounded-full ml-auto">Soon</span>
            </div>
          </nav>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-neon-400/10">
          <div className="glass-card rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="w-3 h-3 text-neon-400" />
              <p className="text-xs text-dark-300">Powered by</p>
            </div>
            <p className="text-sm font-semibold text-white">SpoonOS Framework</p>
            <p className="text-xs text-neon-400/60 mt-1">Neo Blockchain</p>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col h-screen z-10">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 glass-strong border-b border-neon-400/10">
          <div className="flex items-center gap-3 lg:hidden">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-neon-400/30 to-neon-600/20 flex items-center justify-center neon-border">
              <TrendingUp className="w-5 h-5 text-neon-400" />
            </div>
            <h1 className="text-lg font-bold neon-text">VibeTrade</h1>
          </div>
          <div className="hidden lg:block">
            <h2 className="text-sm font-medium text-white">Strategy Chat</h2>
            <p className="text-xs text-dark-400">Describe your investment goals</p>
          </div>
          <ConnectionStatus
            isConnected={isConnected}
            isReconnecting={isReconnecting}
            onReconnect={connect}
          />
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full text-center px-4">
              {/* Hero Icon */}
              <div className="relative mb-8">
                <div className="w-20 h-20 rounded-2xl glass-card flex items-center justify-center neon-glow">
                  <TrendingUp className="w-10 h-10 text-neon-400" />
                </div>
                <div className="absolute -inset-4 bg-neon-400/10 rounded-3xl blur-2xl -z-10" />
              </div>
              
              <h3 className="text-2xl font-bold text-white mb-3">
                Welcome to <span className="neon-text">VibeTrade</span>
              </h3>
              <p className="text-dark-300 max-w-md mb-10 leading-relaxed">
                Describe your portfolio management strategy in plain English. 
                I'll help you build, test, and deploy automated trading strategies.
              </p>
              
              {/* Suggestion Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 w-full max-w-xl">
                {[
                  { text: "Buy BTC when RSI < 30, sell when RSI > 70", icon: "📈" },
                  { text: "Create a momentum strategy for ETH", icon: "⚡" },
                  { text: "DCA into BTC every time it drops 5%", icon: "💰" },
                  { text: "Mean reversion strategy on SOLUSDT", icon: "🔄" },
                ].map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => isConnected && sendMessage(suggestion.text)}
                    disabled={!isConnected}
                    className="group text-left px-5 py-4 glass-card hover:neon-border rounded-xl text-sm text-dark-200 transition-all duration-300 disabled:opacity-40 disabled:cursor-not-allowed hover:scale-[1.02] hover:shadow-glass"
                  >
                    <span className="text-lg mr-2">{suggestion.icon}</span>
                    <span className="group-hover:text-neon-400 transition-colors">{suggestion.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg) => (
            <ChatMessage key={msg.id} message={msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="p-4 glass-strong border-t border-neon-400/10">
          <div className="max-w-3xl mx-auto">
            <ChatInput
              onSendMessage={handleSendMessage}
              disabled={!isConnected}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
