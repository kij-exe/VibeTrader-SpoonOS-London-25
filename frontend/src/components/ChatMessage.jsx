import React, { useState } from 'react';
import { User, Bot, CheckCircle, AlertCircle, Loader2, Play } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import CodeBlock from './CodeBlock';
import BacktestReplay from './BacktestReplay';

const ChatMessage = ({ message }) => {
  const isUser = message.sender === 'user';
  const messageType = message.messageType || 'text';
  const [showReplay, setShowReplay] = useState(false);

  const formatTime = (date) => {
    return new Date(date).toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Get icon based on message type
  const getMessageIcon = () => {
    if (isUser) return <User className="w-4 h-4 text-white" />;
    
    switch (messageType) {
      case 'results':
        return <CheckCircle className="w-4 h-4 text-white" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-white" />;
      case 'progress':
        return <Loader2 className="w-4 h-4 text-white animate-spin" />;
      case 'backtest_replay':
        return <Play className="w-4 h-4 text-white" />;
      default:
        return <Bot className="w-4 h-4 text-white" />;
    }
  };

  // Get background color based on message type
  const getAvatarBg = () => {
    if (isUser) return 'avatar-solid neon-border';
    
    switch (messageType) {
      case 'results':
        return 'avatar-solid-bright neon-glow';
      case 'error':
        return 'avatar-solid-error';
      case 'progress':
        return 'avatar-solid animate-pulse';
      case 'backtest_replay':
        return 'avatar-solid-bright neon-glow';
      default:
        return 'avatar-solid';
    }
  };

  return (
    <div
      className={`message-enter flex gap-4 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-9 h-9 rounded-xl flex items-center justify-center ${getAvatarBg()}`}
      >
        {getMessageIcon()}
      </div>

      {/* Message bubble */}
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[85%]`}>
        <div
          className={`px-5 py-3 rounded-2xl ${
            isUser
              ? 'neon-btn rounded-tr-sm'
              : 'glass-card-solid rounded-tl-sm'
          }`}
        >
          {/* Content - render markdown for agent messages */}
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap text-neon-400">
              {message.content}
            </p>
          ) : (
            <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
              <ReactMarkdown
                components={{
                  // Prevent inline code blocks from rendering (we handle code blocks separately)
                  code: ({ node, inline, ...props }) => 
                    inline ? (
                      <code className="bg-neon-400/10 text-neon-400 px-1.5 py-0.5 rounded text-xs font-mono" {...props} />
                    ) : null,
                  p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                  ul: ({ node, ...props }) => <ul className="list-disc list-inside space-y-1" {...props} />,
                  ol: ({ node, ...props }) => <ol className="list-decimal list-inside space-y-1" {...props} />,
                  strong: ({ node, ...props }) => <strong className="font-semibold text-neon-400" {...props} />,
                }}
              >
                {message.content}
              </ReactMarkdown>
            </div>
          )}
        </div>

        {/* Code blocks (for structured messages) */}
        {message.codeBlocks && message.codeBlocks.length > 0 && (
          <div className="mt-3 w-full">
            {message.codeBlocks.map((block, index) => (
              <CodeBlock
                key={index}
                code={block.code}
                language={block.language || 'python'}
                filename={block.filename}
              />
            ))}
          </div>
        )}

        {/* Backtest Replay Button */}
        {message.backtestData && messageType === 'backtest_replay' && (
          <button
            onClick={() => setShowReplay(true)}
            className="mt-3 flex items-center gap-2 px-5 py-3 neon-btn rounded-xl transition-all transform hover:scale-105 neon-glow"
          >
            <Play className="w-5 h-5" />
            <span className="font-medium">View Order Replay</span>
          </button>
        )}

        {/* Timestamp */}
        <span className="text-xs text-dark-400 mt-1.5 px-1">
          {formatTime(message.timestamp)}
        </span>
      </div>

      {/* Backtest Replay Overlay */}
      {showReplay && message.backtestData && (
        <BacktestReplay
          backtestData={message.backtestData}
          metadata={{
            ...message.metadata,
            initialCapital: 100000,
          }}
          onClose={() => setShowReplay(false)}
        />
      )}
    </div>
  );
};

export default ChatMessage;
