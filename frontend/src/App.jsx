import React, { useEffect, useRef } from 'react';
import { TrendingUp, Zap, Shield, BarChart3 } from 'lucide-react';
import { useWebSocket } from './hooks/useWebSocket';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import ConnectionStatus from './components/ConnectionStatus';

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
    <div className="min-h-screen bg-dark-950 flex">
      {/* Sidebar */}
      <aside className="hidden lg:flex w-72 bg-dark-900 border-r border-dark-800 flex-col">
        {/* Logo */}
        <div className="p-6 border-b border-dark-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-500 to-cyan-500 flex items-center justify-center">
              <TrendingUp className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">VibeTrader</h1>
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
            <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-dark-800/50 text-dark-200">
              <Zap className="w-4 h-4 text-primary-400" />
              <span className="text-sm">Strategy Builder</span>
            </div>
            <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-dark-400 hover:bg-dark-800/30 transition-colors cursor-not-allowed">
              <BarChart3 className="w-4 h-4" />
              <span className="text-sm">Backtesting</span>
              <span className="text-xs bg-dark-700 px-1.5 py-0.5 rounded ml-auto">Soon</span>
            </div>
            <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-dark-400 hover:bg-dark-800/30 transition-colors cursor-not-allowed">
              <Shield className="w-4 h-4" />
              <span className="text-sm">Risk Analysis</span>
              <span className="text-xs bg-dark-700 px-1.5 py-0.5 rounded ml-auto">Soon</span>
            </div>
          </nav>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-dark-800">
          <div className="bg-gradient-to-r from-primary-900/30 to-cyan-900/30 rounded-xl p-4">
            <p className="text-xs text-dark-300 mb-2">Powered by</p>
            <p className="text-sm font-semibold text-white">SpoonOS Framework</p>
            <p className="text-xs text-dark-400 mt-1">Neo Blockchain</p>
          </div>
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col h-screen">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-dark-800 bg-dark-900/50 backdrop-blur-sm">
          <div className="flex items-center gap-3 lg:hidden">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-cyan-500 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-lg font-bold text-white">VibeTrader</h1>
          </div>
          <div className="hidden lg:block">
            <h2 className="text-sm font-medium text-dark-200">Strategy Chat</h2>
            <p className="text-xs text-dark-500">Describe your investment goals</p>
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
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary-500/20 to-cyan-500/20 flex items-center justify-center mb-6">
                <TrendingUp className="w-8 h-8 text-primary-400" />
              </div>
              <h3 className="text-xl font-semibold text-white mb-2">
                Welcome to VibeTrader
              </h3>
              <p className="text-dark-400 max-w-md mb-8">
                Describe your portfolio management strategy in plain English. 
                I'll help you build, test, and deploy automated trading strategies.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 w-full max-w-lg">
                {[
                  "I want to invest 100 USDC with medium risk",
                  "Create a momentum-based strategy for BTC",
                  "I need a conservative DCA strategy",
                  "Build a mean reversion strategy for ETH",
                ].map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => isConnected && sendMessage(suggestion)}
                    disabled={!isConnected}
                    className="text-left px-4 py-3 bg-dark-800 hover:bg-dark-700 border border-dark-700 rounded-xl text-sm text-dark-300 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {suggestion}
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
        <div className="p-4 border-t border-dark-800 bg-dark-900/50 backdrop-blur-sm">
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
