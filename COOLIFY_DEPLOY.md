# Deploying to Coolify

This guide explains how to deploy the Crypto Trading Bot with Dashboard to Coolify.

## Prerequisites

1. A Coolify instance running on your server
2. Docker installed on the server
3. Binance API credentials (testnet or production)

## Deployment Steps

### 1. Create a New Project in Coolify

1. Log in to your Coolify dashboard
2. Click "New Project" and give it a name (e.g., "Trading Bot")

### 2. Add a New Resource

1. Inside your project, click "Add New Resource"
2. Select "Docker Compose" or "Dockerfile"

### 3. Configure the Repository

**Option A: From GitHub (Recommended)**

1. Connect your GitHub account to Coolify
2. Select the repository containing this code
3. Coolify will automatically detect the Dockerfile

**Option B: Manual Upload**

1. Upload the project files directly to your server
2. Point Coolify to the local directory

### 4. Configure Environment Variables

In Coolify, go to "Environment Variables" and add:

```
TRADING_MODE=TESTNET
BINANCE_TESTNET_API_KEY=your_api_key
BINANCE_TESTNET_API_SECRET=your_api_secret
TRADING_PAIR=BTCUSDT
INITIAL_CAPITAL=100
MAX_LEVERAGE=2
RISK_PER_TRADE=0.01
TELEGRAM_BOT_TOKEN=your_telegram_bot_token (optional)
TELEGRAM_CHAT_ID=your_chat_id (optional)
```

### 5. Configure Domain

1. Go to "Settings" > "Domain"
2. Add your domain: `trading.arlexperalta.com`
3. Enable "HTTPS" (Coolify will handle SSL via Let's Encrypt)

### 6. Configure Port

1. Make sure port 8000 is exposed
2. Coolify will automatically configure the reverse proxy

### 7. Deploy

1. Click "Deploy"
2. Wait for the build and deployment to complete
3. Access your dashboard at `https://trading.arlexperalta.com`

## Health Check

The bot exposes a health endpoint at `/api/health` which Coolify can use for monitoring:

```
GET https://trading.arlexperalta.com/api/health
```

## Logs

You can view logs in Coolify's dashboard or by running:

```bash
docker logs crypto-trading-bot
```

## Updating

To update the bot:

1. Push changes to your GitHub repository
2. Coolify will automatically redeploy (if auto-deploy is enabled)
3. Or manually click "Redeploy" in the Coolify dashboard

## Troubleshooting

### Bot not starting

1. Check environment variables are set correctly
2. Verify Binance API credentials are valid
3. Check logs for error messages

### Dashboard not accessible

1. Verify domain DNS is pointing to your server
2. Check that port 8000 is not blocked by firewall
3. Ensure Coolify's reverse proxy is configured correctly

### Connection to Binance failing

1. Verify your server can reach Binance API
2. Check if you're using testnet credentials with TESTNET mode
3. Ensure API keys have futures trading permissions

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/` | Dashboard UI |
| `/api/status` | Full bot status |
| `/api/health` | Health check |
| `/api/trades` | Trade history |
| `/api/logs` | Recent logs |
| `/api/stats` | Daily statistics |

## Support

For issues or questions:
- Check the README.md for general documentation
- Review Coolify's documentation for deployment issues
- Check Binance API documentation for trading issues
