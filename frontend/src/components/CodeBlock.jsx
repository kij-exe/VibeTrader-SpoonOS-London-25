import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, Download } from 'lucide-react';

const CodeBlock = ({ code, language = 'python', filename }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const blob = new Blob([code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename || `code.${language}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="my-4 rounded-xl overflow-hidden glass-card">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-black/30 border-b border-neon-400/10">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-red-500/80"></div>
          <div className="w-2 h-2 rounded-full bg-yellow-500/80"></div>
          <div className="w-2 h-2 rounded-full bg-neon-400/80"></div>
          {filename && (
            <span className="text-xs text-dark-300 ml-2 font-mono">{filename}</span>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-xs text-neon-400/60 uppercase font-mono">{language}</span>
          <button
            onClick={handleCopy}
            className="p-1.5 hover:bg-neon-400/10 rounded-lg transition-colors group"
            title="Copy code"
          >
            {copied ? (
              <Check className="w-4 h-4 text-neon-400" />
            ) : (
              <Copy className="w-4 h-4 text-dark-400 group-hover:text-neon-400" />
            )}
          </button>
          <button
            onClick={handleDownload}
            className="p-1.5 hover:bg-neon-400/10 rounded-lg transition-colors group"
            title="Download code"
          >
            <Download className="w-4 h-4 text-dark-400 group-hover:text-neon-400" />
          </button>
        </div>
      </div>

      {/* Code */}
      <div className="max-h-96 overflow-auto custom-scrollbar bg-black/40">
        <SyntaxHighlighter
          language={language}
          style={vscDarkPlus}
          customStyle={{
            margin: 0,
            padding: '1rem',
            background: 'transparent',
            fontSize: '0.875rem',
          }}
          showLineNumbers={true}
          wrapLines={true}
        >
          {code}
        </SyntaxHighlighter>
      </div>
    </div>
  );
};

export default CodeBlock;
