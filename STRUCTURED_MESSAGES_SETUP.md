# Structured Messages Setup Guide

## Installation

### 1. Install Frontend Dependencies

```bash
cd frontend
npm install
```

This will install the newly added packages:
- `react-markdown@^9.0.1` - For rendering markdown in messages
- `react-syntax-highlighter@^15.5.0` - For code syntax highlighting

### 2. No Backend Changes Needed
The backend changes are already in place - no additional dependencies required.

---

## Quick Start

### Backend Usage

```python
# In any node function
from app.message_types import create_results_message

# Send structured message with code
message = create_results_message(
    content="✅ **Strategy Ready!**\n\nBacktest completed successfully.",
    code=strategy_code,
    language="python",
    metadata={"metrics": backtest_metrics}
)

await callback(message)
```

### Frontend - Automatic!
The frontend automatically:
- Detects message types
- Renders code with syntax highlighting
- Shows appropriate icons
- Formats markdown

---

## Testing

### 1. Start Backend
```bash
cd backend
uvicorn app.main:app --reload
```

### 2. Start Frontend
```bash
cd frontend
npm run dev
```

### 3. Open Browser
Navigate to `http://localhost:5173`

### 4. Test Messages
Request a strategy from the chatbot and see:
- Progress messages with spinning loader
- Final results with syntax-highlighted code
- Copy/download buttons on code blocks

---

## Features to Test

### ✅ Syntax Highlighting
- Python code should have colored syntax
- Line numbers on the left
- VS Code Dark+ theme

### ✅ Code Actions
- Click copy button → code copied to clipboard
- Click download → code downloaded as .py file
- Shows filename if provided

### ✅ Message Types
- **Progress**: Blue avatar, spinning icon
- **Results**: Green avatar, checkmark icon
- **Error**: Red avatar, alert icon
- **Text**: Cyan avatar, bot icon

### ✅ Markdown Rendering
- **Bold** text works
- Lists render properly
- Links are clickable
- Inline `code` is styled

---

## Files Modified

### Backend
```
backend/
├── app/
│   ├── message_types.py          ← NEW: Message format definitions
│   ├── websocket_manager.py      ← UPDATED: Support structured messages
│   └── agent/
│       └── agent.py               ← UPDATED: Send structured messages
```

### Frontend
```
frontend/
├── package.json                   ← UPDATED: New dependencies
├── src/
│   ├── index.css                  ← UPDATED: Scrollbar & prose styling
│   ├── hooks/
│   │   └── useWebSocket.js        ← UPDATED: Parse structured messages
│   └── components/
│       ├── CodeBlock.jsx          ← NEW: Code display component
│       └── ChatMessage.jsx        ← UPDATED: Handle structured messages
```

---

## Troubleshooting

### Issue: "Module not found: react-syntax-highlighter"
**Solution**: Run `npm install` in frontend directory

### Issue: Code blocks not highlighting
**Solution**: 
1. Check browser console for errors
2. Verify npm packages installed
3. Try clearing browser cache

### Issue: Copy button not working
**Solution**: 
- Ensure you're on HTTPS or localhost
- Check browser clipboard permissions

### Issue: CSS warnings about @tailwind
**Solution**: These are expected - Tailwind CSS directives are processed by PostCSS at build time. Not actual errors.

---

## Development Tips

### Adding New Message Types

1. **Define in `message_types.py`**:
```python
def create_custom_message(content: str) -> Dict[str, Any]:
    return {
        "message_type": "custom",
        "content": content,
        "metadata": {}
    }
```

2. **Add icon in `ChatMessage.jsx`**:
```javascript
case 'custom':
  return <CustomIcon className="w-4 h-4 text-white" />;
```

3. **Add avatar color**:
```javascript
case 'custom':
  return 'bg-gradient-to-br from-purple-500 to-pink-500';
```

### Customizing Code Theme

Edit `CodeBlock.jsx`:
```javascript
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
// Then use: style={oneDark}
```

Available themes:
- `vscDarkPlus` (default)
- `oneDark`
- `dracula`
- `atomDark`
- `nightOwl`

---

## Performance

### Bundle Size
- `react-syntax-highlighter`: ~50KB gzipped
- `react-markdown`: ~20KB gzipped

### Optimization Tips
1. Lazy load syntax highlighter if needed
2. Limit max code block height
3. Virtualize long message lists
4. Memoize message components

---

## Next Steps

1. ✅ Install dependencies
2. ✅ Test basic functionality
3. ✅ Verify code highlighting works
4. ✅ Check copy/download features
5. 📝 Consider custom themes
6. 📝 Add more message types as needed

---

## Support

For issues or questions:
1. Check browser console for errors
2. Verify all dependencies installed
3. Ensure backend/frontend versions match
4. Review STRUCTURED_MESSAGES_GUIDE.md

---

**Ready to use!** 🎉

The system is now capable of sending beautiful, syntax-highlighted code blocks with interactive features.
