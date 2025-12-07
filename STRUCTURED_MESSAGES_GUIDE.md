# Structured Messages System

## Overview

The VibeTrader frontend-backend communication now supports **structured messages** with rich formatting, code blocks with syntax highlighting, and different message types.

---

## Message Format

### Backend → Frontend

```json
{
  "type": "message",
  "message_type": "text|code|progress|results|error|system",
  "content": "Markdown-formatted text",
  "code_blocks": [
    {
      "language": "python",
      "code": "from AlgorithmImports import *...",
      "filename": "strategy.py"
    }
  ],
  "metadata": {
    "metrics": {...},
    "strategy_spec": {...}
  }
}
```

---

## Message Types

### 1. **Text Message** (Default)
Simple text communication.

```python
from app.message_types import create_text_message

message = create_text_message(
    "Analyzing your requirements...",
    metadata={"step": "entry"}
)
await callback(message)
```

**Frontend Display**:
- 🤖 Bot icon
- Cyan/emerald gradient avatar
- Markdown rendering

---

### 2. **Code Message**
Message with code block and syntax highlighting.

```python
from app.message_types import create_code_message

message = create_code_message(
    content="Here's your generated strategy:",
    code=strategy_code,
    language="python",
    filename="strategy.py",
    metadata={"strategy_name": "BTCStrategy"}
)
await callback(message)
```

**Frontend Display**:
- Syntax-highlighted code block
- Copy/download buttons
- Line numbers
- VS Code Dark+ theme

---

### 3. **Progress Message**
Status updates during processing.

```python
from app.message_types import create_progress_message

message = create_progress_message(
    "🔄 **Running Backtest**\n"
    "  • Symbol: BTCUSDT\n"
    "  • Timeframe: 1h\n"
    "⏳ This may take a few seconds...",
    metadata={"stage": "compile"}
)
await callback(message)
```

**Frontend Display**:
- ⏳ Spinning loader icon
- Blue gradient avatar
- Real-time updates

---

### 4. **Results Message**
Final results with code and metrics.

```python
from app.message_types import create_results_message

message = create_results_message(
    content="✅ **Strategy Backtest Results**\n\n"
            "✅ Backtest completed successfully:\n"
            "  • Return: +12.34%\n"
            "  • Max Drawdown: 15.67%\n"
            "  • Win Rate: 56.5%",
    code=strategy_code,
    language="python",
    metadata={
        "metrics": {...},
        "strategy_spec": {...}
    }
)
await callback(message)
```

**Frontend Display**:
- ✅ CheckCircle icon
- Green gradient avatar
- Code block below message
- Structured metrics

---

### 5. **Error Message**
Error notifications.

```python
from app.message_types import create_error_message

message = create_error_message(
    "❌ **Backtest Failed**\n\n"
    "The trading pair 'XAUUSD' is not available on Binance.\n\n"
    "Please specify a valid pair (e.g., BTCUSDT, ETHUSDT).",
    metadata={"error_type": "symbol"}
)
await callback(message)
```

**Frontend Display**:
- ⚠️ AlertCircle icon
- Red/orange gradient avatar
- Error formatting

---

## Code Block Features

### Syntax Highlighting
- **Theme**: VS Code Dark Plus
- **Languages**: Python, JavaScript, JSON, etc.
- **Line Numbers**: Enabled
- **Scrollable**: Max height 96 (24rem)

### Interactive Features
1. **Copy Button** - Copy code to clipboard
2. **Download Button** - Download code as file
3. **Filename Display** - Show file name in header
4. **Language Badge** - Display code language

### Example:

```python
# Code block with all features
CodeBlock:
  ├── Header
  │   ├── Traffic lights (🔴 🟡 🟢)
  │   ├── Filename: "strategy.py"
  │   └── Actions: Copy | Download
  └── Code Content
      ├── Line numbers
      ├── Syntax highlighting
      └── Scrollable content
```

---

## Frontend Components

### 1. **CodeBlock.jsx**
Standalone code display component.

```jsx
<CodeBlock
  code={strategyCode}
  language="python"
  filename="strategy.py"
/>
```

### 2. **ChatMessage.jsx**
Enhanced message component with:
- Message type detection
- Dynamic avatar icons
- Markdown rendering
- Code block integration
- Timestamp display

---

## Backend Integration

### websocket_manager.py
Supports both plain text (legacy) and structured messages.

```python
# Plain text (auto-wrapped)
await manager.send_message(client_id, "Hello!")

# Structured message
await manager.send_message(client_id, {
    "message_type": "results",
    "content": "Results ready!",
    "code_blocks": [...]
})
```

### agent.py
Updated `_respond_node` to send structured messages:

```python
from app.message_types import create_results_message

structured_message = create_results_message(
    content=backtest_summary,
    code=strategy_code,
    language="python",
    metadata={
        "metrics": metrics,
        "strategy_spec": strategy_spec
    }
)

await callback(structured_message)
```

---

## Frontend Integration

### useWebSocket.js Hook
Parses structured messages:

```javascript
const message = {
  id: Date.now() + Math.random(),
  sender: 'agent',
  timestamp: new Date(),
  messageType: data.message_type || 'text',
  content: data.content,
  codeBlocks: data.code_blocks || null,
  metadata: data.metadata || null,
};
```

---

## Visual Design

### Avatar Colors

| Message Type | Icon | Color Gradient |
|--------------|------|----------------|
| User         | 👤   | Primary Blue |
| Text         | 🤖   | Cyan/Emerald |
| Progress     | ⏳   | Blue/Cyan |
| Results      | ✅   | Green/Emerald |
| Error        | ⚠️   | Red/Orange |

### Code Block Theme
- **Background**: Dark (#1e1e1e)
- **Header**: Dark gray (#1a1a1a)
- **Border**: Subtle (#374151)
- **Text**: Light (#e5e7eb)
- **Keywords**: Highlighted (theme-dependent)

---

## Installation

### Backend
```bash
# Already included - no additional packages needed
```

### Frontend
```bash
cd frontend
npm install react-markdown react-syntax-highlighter
```

---

## Usage Examples

### Example 1: Simple Progress Update

```python
from app.message_types import create_progress_message

await _send_progress(state, create_progress_message(
    "📋 **Requirements Confirmed**\n"
    "  • Symbol: BTCUSDT\n"
    "  • Timeframe: 1h\n\n"
    "🛠️ Generating strategy code..."
))
```

### Example 2: Results with Code

```python
from app.message_types import create_results_message

message = create_results_message(
    content=f"✅ **Backtest Complete!**\n\n{summary}",
    code=strategy_code,
    language="python",
    metadata={"metrics": metrics}
)
await callback(message)
```

### Example 3: Error with Context

```python
from app.message_types import create_error_message

message = create_error_message(
    f"⚠️ Invalid timeframe '{timeframe}'.\n\n"
    f"Valid: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w, 1M",
    metadata={"error_type": "validation"}
)
await callback(message)
```

---

## Benefits

### ✅ Rich Formatting
- Markdown support
- Bold, italic, lists
- Links and inline code

### ✅ Syntax Highlighting
- Professional code display
- VS Code theme
- Line numbers
- Language detection

### ✅ Interactive Code
- Copy to clipboard
- Download as file
- Filename display
- Scrollable for long code

### ✅ Visual Hierarchy
- Message type icons
- Color-coded avatars
- Consistent design
- Clear structure

### ✅ Better UX
- Real-time progress updates
- Clear error messages
- Organized results
- Professional appearance

---

## Future Enhancements

- [ ] **Diff View** - Show code changes
- [ ] **Collapsible Sections** - Long code blocks
- [ ] **Theme Selector** - User preference
- [ ] **Export Chat** - Download conversation
- [ ] **Search in Code** - Find text in code blocks
- [ ] **Multiple Languages** - Support for more languages

---

## Technical Details

### Dependencies

**Backend**:
- `pydantic` - Message validation
- `fastapi` - WebSocket support

**Frontend**:
- `react-markdown` - Markdown rendering
- `react-syntax-highlighter` - Code highlighting
- `lucide-react` - Icons

### Performance

- **Code Splitting**: Syntax highlighter lazy-loaded
- **Virtual Scrolling**: For long code blocks
- **Efficient Rendering**: React.memo optimizations
- **Debounced Updates**: Smooth progress messages

---

## Migration Notes

### Backward Compatibility
Plain text messages still work - they're auto-converted to structured format:

```python
# Old way (still works)
await callback("Hello!")

# New way (recommended)
await callback(create_text_message("Hello!"))
```

### Gradual Migration
You can migrate incrementally:
1. Use structured messages for new features
2. Keep plain text for simple messages
3. Migrate critical paths first

---

## Troubleshooting

### Code Not Highlighting
- Check `language` field matches supported language
- Ensure `react-syntax-highlighter` is installed
- Verify code string is properly formatted

### Message Not Displaying
- Check WebSocket connection
- Verify message format matches schema
- Check browser console for errors

### Copy/Download Not Working
- Ensure HTTPS for clipboard API (or localhost)
- Check browser permissions
- Verify Blob API support

---

## Contributing

When adding new message types:

1. Update `message_types.py`
2. Add helper function
3. Update frontend ChatMessage component
4. Add icon and avatar color
5. Document in this guide

---

## License

Part of VibeTrader project - MIT License

---

**Last Updated**: 2025-12-07  
**Version**: 1.0.0  
**Status**: Production Ready ✅
