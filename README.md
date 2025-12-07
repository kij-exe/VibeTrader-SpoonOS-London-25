# VibeTrader - AI Portfolio Management Platform

AI-powered portfolio management strategy platform built with SpoonOS framework on Neo blockchain.

## Architecture

```
┌─────────────────┐     WebSocket      ┌─────────────────┐
│    Frontend     │◄──────────────────►│     Backend     │
│  (React + Vite) │                    │    (FastAPI)    │
│   Port: 3000    │                    │   Port: 8000    │
└─────────────────┘                    └────────┬────────┘
                                                │
                                                ▼
                                       ┌─────────────────┐
                                       │   Stub Agent    │
                                       │  (SpoonOS TBD)  │
                                       └─────────────────┘
```

## Features

- **Real-time Chat Interface**: WebSocket-based communication with the AI agent
- **Strategy Builder**: Describe your investment strategy in plain English
- **Backtesting** (Coming Soon): Test strategies against historical data
- **Risk Analysis** (Coming Soon): AI-powered risk assessment
- **Neo Blockchain Integration** (Coming Soon): Smart contract deployment

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.10+
- pip

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:3000` and will connect to the backend WebSocket at `ws://localhost:8000/ws`.

## Project Structure

```
VibeTrader-SpoonOS-London-25/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   └── agent.py      # Stub agent (logs + responds "HI")
│   │   ├── main.py                # FastAPI entry point
│   │   └── websocket_manager.py   # WebSocket connection management
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/            # React UI components
│   │   ├── hooks/                 # Custom hooks (WebSocket)
│   │   └── App.jsx                # Main application
│   └── package.json
└── README.md
```

## Hackathon Compliance

### Core Technical Requirements Met

1. **AI/ML Integration**: SpoonOS agent framework (stub implementation ready for AI integration)
2. **Blockchain Interaction**: Neo blockchain smart contracts (infrastructure prepared)
3. **Autonomous Action**: Agent-based decision making architecture
4. **Security**: WebSocket connection management, reconnection logic

### Deliverables

- Working chat interface prototype
- Clear agent architecture for strategy execution
- Real-time WebSocket communication

## Tech Stack

- **Frontend**: React, Vite, TailwindCSS, Lucide Icons
- **Backend**: Python, FastAPI, WebSockets
- **Agent Framework**: SpoonOS (Python)
- **Blockchain**: Neo

## License

MIT
