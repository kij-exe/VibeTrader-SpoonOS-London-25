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
    if (isUser) return 'bg-primary-600';
    
    switch (messageType) {
      case 'results':
        return 'bg-gradient-to-br from-green-500 to-emerald-500';
      case 'error':
        return 'bg-gradient-to-br from-red-500 to-orange-500';
      case 'progress':
        return 'bg-gradient-to-br from-blue-500 to-cyan-500';
      case 'backtest_replay':
        return 'bg-gradient-to-br from-purple-500 to-pink-500';
      default:
        return 'bg-gradient-to-br from-emerald-500 to-cyan-500';
    }
  };

  return (
    <div
      className={`message-enter flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${getAvatarBg()}`}
      >
        {getMessageIcon()}
      </div>

      {/* Message bubble */}
      <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} max-w-[85%]`}>
        <div
          className={`px-4 py-2.5 rounded-2xl ${
            isUser
              ? 'bg-primary-600 text-white rounded-tr-sm'
              : 'bg-dark-800 text-dark-100 rounded-tl-sm'
          }`}
        >
          {/* Content - render markdown for agent messages */}
          {isUser ? (
            <p className="text-sm leading-relaxed whitespace-pre-wrap">
              {message.content}
            </p>
          ) : (
            <div className="text-sm leading-relaxed prose prose-invert prose-sm max-w-none">
              <ReactMarkdown
                components={{
                  // Prevent inline code blocks from rendering (we handle code blocks separately)
                  code: ({ node, inline, ...props }) => 
                    inline ? (
                      <code className="bg-dark-700 px-1.5 py-0.5 rounded text-xs font-mono" {...props} />
                    ) : null,
                  p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
                  ul: ({ node, ...props }) => <ul className="list-disc list-inside space-y-1" {...props} />,
                  ol: ({ node, ...props }) => <ol className="list-decimal list-inside space-y-1" {...props} />,
                  strong: ({ node, ...props }) => <strong className="font-semibold text-white" {...props} />,
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
            className="mt-3 flex items-center gap-2 px-4 py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 rounded-xl transition-all transform hover:scale-105 shadow-lg"
          >
            <Play className="w-5 h-5 text-white" />
            <span className="font-medium text-white">View Order Replay</span>
          </button>
        )}

        {/* Timestamp */}
        <span className="text-xs text-dark-500 mt-1 px-1">
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
