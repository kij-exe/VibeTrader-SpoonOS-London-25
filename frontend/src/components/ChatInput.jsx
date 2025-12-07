import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip } from 'lucide-react';

const ChatInput = ({ onSendMessage, disabled }) => {
  const [message, setMessage] = useState('');
  const textareaRef = useRef(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    const trimmedMessage = message.trim();
    if (trimmedMessage && !disabled) {
      onSendMessage(trimmedMessage);
      setMessage('');
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 150)}px`;
    }
  }, [message]);

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className="flex items-end gap-2 glass-input rounded-2xl p-3 focus-within:border-neon-400/40 focus-within:shadow-neon transition-all">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe your investment strategy..."
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent text-white placeholder-dark-400 resize-none outline-none px-2 py-1.5 text-sm max-h-[150px]"
        />
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="p-2 text-dark-400 hover:text-neon-400 transition-colors rounded-lg hover:bg-neon-400/10"
            title="Attach file (coming soon)"
            disabled
          >
            <Paperclip className="w-5 h-5" />
          </button>
          <button
            type="submit"
            disabled={!message.trim() || disabled}
            className={`p-2.5 rounded-xl transition-all duration-300 ${
              message.trim() && !disabled
                ? 'neon-btn neon-glow'
                : 'bg-dark-700/50 text-dark-500 cursor-not-allowed'
            }`}
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
      {disabled && (
        <p className="text-xs text-neon-400/70 mt-2 text-center flex items-center justify-center gap-2">
          <span className="w-2 h-2 bg-neon-400 rounded-full animate-pulse" />
          Connecting to server...
        </p>
      )}
    </form>
  );
};

export default ChatInput;
