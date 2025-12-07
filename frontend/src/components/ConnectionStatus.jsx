import React from 'react';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';

const ConnectionStatus = ({ isConnected, isReconnecting, onReconnect }) => {
  if (isConnected) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs">
        <span className="w-2 h-2 bg-neon-400 rounded-full animate-pulse shadow-neon" />
        <Wifi className="w-3.5 h-3.5 text-neon-400" />
        <span className="text-neon-400">Connected</span>
      </div>
    );
  }

  if (isReconnecting) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs">
        <RefreshCw className="w-3.5 h-3.5 text-amber-400 animate-spin" />
        <span className="text-amber-400">Reconnecting...</span>
      </div>
    );
  }

  return (
    <button
      onClick={onReconnect}
      className="flex items-center gap-2 px-3 py-1.5 rounded-full glass text-xs hover:bg-red-500/10 transition-all"
    >
      <WifiOff className="w-3.5 h-3.5 text-red-400" />
      <span className="text-red-400">Disconnected - Click to reconnect</span>
    </button>
  );
};

export default ConnectionStatus;
