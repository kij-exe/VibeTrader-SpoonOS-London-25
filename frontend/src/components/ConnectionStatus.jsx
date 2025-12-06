import React from 'react';
import { Wifi, WifiOff, RefreshCw } from 'lucide-react';

const ConnectionStatus = ({ isConnected, isReconnecting, onReconnect }) => {
  if (isConnected) {
    return (
      <div className="flex items-center gap-2 text-emerald-400 text-xs">
        <Wifi className="w-3.5 h-3.5" />
        <span>Connected</span>
      </div>
    );
  }

  if (isReconnecting) {
    return (
      <div className="flex items-center gap-2 text-amber-400 text-xs">
        <RefreshCw className="w-3.5 h-3.5 animate-spin" />
        <span>Reconnecting...</span>
      </div>
    );
  }

  return (
    <button
      onClick={onReconnect}
      className="flex items-center gap-2 text-red-400 text-xs hover:text-red-300 transition-colors"
    >
      <WifiOff className="w-3.5 h-3.5" />
      <span>Disconnected - Click to reconnect</span>
    </button>
  );
};

export default ConnectionStatus;
