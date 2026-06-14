import logging
import sys
import os
import uvicorn
from src.config import settings

def setup_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )

def main() -> None:
    setup_logging()
    logger = logging.getLogger("linmap-bot")
    
    # Determine execution mode from CLI arguments or environment variable
    mode = "api"
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
    else:
        mode = os.environ.get("APP_MODE", "api").lower()
        
    if mode == "api":
        logger.info(f"Starting Linmap API on {settings.API_HOST}:{settings.API_PORT}...")
        uvicorn.run("src.api.app:app", host=settings.API_HOST, port=settings.API_PORT, reload=False)
    elif mode == "bot":
        logger.info("Starting Linmap Discord Bot...")
        from src.bot.discord_client import main as bot_main
        bot_main()
    else:
        logger.error(f"Unknown mode: {mode}. Please specify 'api' or 'bot'.")
        sys.exit(1)

if __name__ == "__main__":
    main()
