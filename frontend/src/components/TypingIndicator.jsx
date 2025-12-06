import React from 'react';
import { Bot } from 'lucide-react';

const TypingIndicator = () => {
  return (
    <div className="flex gap-3 message-enter">
      <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center bg-gradient-to-br from-emerald-500 to-cyan-500">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="bg-dark-800 px-4 py-3 rounded-2xl rounded-tl-sm">
        <div className="flex gap-1">
          <div className="typing-dot w-2 h-2 bg-dark-400 rounded-full"></div>
          <div className="typing-dot w-2 h-2 bg-dark-400 rounded-full"></div>
          <div className="typing-dot w-2 h-2 bg-dark-400 rounded-full"></div>
        </div>
      </div>
    </div>
  );
};

export default TypingIndicator;
