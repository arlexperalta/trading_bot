"""
Quick test script for Telegram notifications.
Run this to verify Telegram integration is working.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import Settings
from src.utils.telegram_notifier import notifier


def main():
    """Test Telegram notifications"""
    print("\n" + "=" * 60)
    print("Testing Telegram Notifications")
    print("=" * 60)

    if not notifier.enabled:
        print("\n❌ Telegram notifications are DISABLED")
        print("Please configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in config/.env")
        return

    print(f"\n✅ Telegram notifications are ENABLED")
    print(f"Bot Token: {Settings.TELEGRAM_BOT_TOKEN[:20]}...")
    print(f"Chat ID: {Settings.TELEGRAM_CHAT_ID}")

    print("\n" + "-" * 60)
    print("Sending test message...")
    print("-" * 60)

    # Send a simple test message
    success = notifier.send_message(
        "🧪 <b>Telegram Test</b>\n\nThis is a test message from your trading bot!\n\n✅ Notifications are working correctly."
    )

    if success:
        print("\n✅ Test message sent successfully!")
        print("Check your Telegram to verify you received the message.")
    else:
        print("\n❌ Failed to send test message")
        print("Please check:")
        print("  1. Bot token is correct")
        print("  2. Chat ID is correct")
        print("  3. You have started a conversation with the bot")
        print("  4. Internet connection is working")

    print("\n" + "=" * 60)
    print("Testing different notification types...")
    print("=" * 60)

    # Test bot start notification
    print("\n1. Testing bot start notification...")
    notifier.notify_bot_start()

    # Test trade entry notification
    print("2. Testing trade entry notification...")
    notifier.notify_trade_entry(
        side="LONG",
        price=50000.0,
        quantity=0.001,
        stop_loss=49000.0,
        take_profit=53000.0
    )

    # Test trade exit notification
    print("3. Testing trade exit notification...")
    notifier.notify_trade_exit(
        side="LONG",
        entry_price=50000.0,
        exit_price=52000.0,
        quantity=0.001,
        pnl=2.0,
        pnl_percent=4.0,
        reason="Take Profit"
    )

    # Test balance update
    print("4. Testing balance update notification...")
    notifier.notify_balance_update(balance=1000.0, unrealized_pnl=50.0)

    # Test error notification
    print("5. Testing error notification...")
    notifier.notify_error("Test Error", "This is a test error message")

    # Test daily summary
    print("6. Testing daily summary notification...")
    notifier.notify_daily_summary(
        trades_today=5,
        wins=3,
        losses=2,
        total_pnl=25.50,
        win_rate=60.0
    )

    # Test bot stop notification
    print("7. Testing bot stop notification...")
    notifier.notify_bot_stop("Test completed")

    print("\n" + "=" * 60)
    print("✅ All test notifications sent!")
    print("Check your Telegram to verify all messages were received.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
