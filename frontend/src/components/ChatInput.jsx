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
      <div className="flex items-end gap-2 bg-dark-800 rounded-2xl p-2 border border-dark-700 focus-within:border-primary-500 transition-colors">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Describe your investment strategy..."
          disabled={disabled}
          rows={1}
          className="flex-1 bg-transparent text-dark-100 placeholder-dark-500 resize-none outline-none px-2 py-1.5 text-sm max-h-[150px]"
        />
        <div className="flex items-center gap-1">
          <button
            type="button"
            className="p-2 text-dark-500 hover:text-dark-300 transition-colors rounded-lg hover:bg-dark-700"
            title="Attach file (coming soon)"
            disabled
          >
            <Paperclip className="w-5 h-5" />
          </button>
          <button
            type="submit"
            disabled={!message.trim() || disabled}
            className={`p-2 rounded-xl transition-all ${
              message.trim() && !disabled
                ? 'bg-primary-600 text-white hover:bg-primary-500'
                : 'bg-dark-700 text-dark-500 cursor-not-allowed'
            }`}
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
      {disabled && (
        <p className="text-xs text-amber-500 mt-2 text-center">
          Connecting to server...
        </p>
      )}
    </form>
  );
};

export default ChatInput;
