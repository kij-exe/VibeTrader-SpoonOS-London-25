import React from 'react';
import { Bot } from 'lucide-react';

const TypingIndicator = () => {
  return (
    <div className="flex gap-4 message-enter">
      <div className="flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center bg-gradient-to-br from-neon-400/20 to-neon-600/10">
        <Bot className="w-4 h-4 text-neon-400" />
      </div>
      <div className="glass-card px-5 py-3.5 rounded-2xl rounded-tl-sm">
        <div className="flex gap-1.5">
          <div className="typing-dot"></div>
          <div className="typing-dot"></div>
          <div className="typing-dot"></div>
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;
