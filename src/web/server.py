"""
FastAPI web server for the trading bot dashboard.
"""

import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime

from src.web.bot_state import bot_state

# Create FastAPI app
app = FastAPI(
    title="Crypto Trading Bot Dashboard",
    description="Real-time monitoring dashboard for the Binance Futures trading bot",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files directory
STATIC_DIR = Path(__file__).parent / "static"


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main dashboard."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)


@app.get("/api/status")
async def get_status():
    """Get current bot status and state."""
    state = bot_state.get_state()
    return {
        "success": True,
        "data": state,
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Coolify/Docker."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/trades")
async def get_trades():
    """Get trade history."""
    state = bot_state.get_state()
    return {
        "success": True,
        "trades": state["trade_history"],
        "total": len(state["trade_history"])
    }


@app.get("/api/logs")
async def get_logs():
    """Get recent logs."""
    state = bot_state.get_state()
    return {
        "success": True,
        "logs": state["recent_logs"],
        "total": len(state["recent_logs"])
    }


@app.get("/api/stats")
async def get_stats():
    """Get daily statistics."""
    state = bot_state.get_state()

    # Calculate uptime
    uptime_seconds = 0
    if state["started_at"]:
        started = datetime.fromisoformat(state["started_at"])
        uptime_seconds = (datetime.now() - started).total_seconds()

    # Calculate profit percentage
    profit_pct = 0.0
    if state["initial_capital"] > 0:
        profit_pct = ((state["balance_total"] - state["initial_capital"]) / state["initial_capital"]) * 100

    return {
        "success": True,
        "stats": {
            "is_running": state["is_running"],
            "uptime_seconds": uptime_seconds,
            "iteration": state["iteration"],
            "balance_total": state["balance_total"],
            "balance_available": state["balance_available"],
            "initial_capital": state["initial_capital"],
            "profit_pct": profit_pct,
            "daily_trades": state["daily_trades"],
            "daily_wins": state["daily_wins"],
            "daily_losses": state["daily_losses"],
            "daily_pnl": state["daily_pnl"],
            "daily_win_rate": state["daily_win_rate"],
        }
    }


# Mount static files (CSS, JS, images)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
