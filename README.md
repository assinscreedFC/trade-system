# trade-system

Scaffold project for a crypto scanner + aiogram bot.
Structure created by bootstrap_trade_system.ps1.

Folders:
- config/
- services/scanner/
- services/bot/
- services/worker/
- .github/workflows/

Edit the templates in `services/*/src/` to implement your logic.

docker run -d --name redis -p 6379:6379 redis