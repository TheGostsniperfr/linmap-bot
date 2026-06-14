import logging
import io
import discord
from datetime import datetime, timezone
from src.config import settings
from src.bot.api_client import LinmapAPIClient

logger = logging.getLogger("linmap-cron")
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

class CronClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.api_client = LinmapAPIClient()

    async def setup_hook(self):
        self.loop.create_task(self.run_sync_and_exit())

    async def run_sync_and_exit(self):
        await self.wait_until_ready()
        logger.info("CronJob Triggered: Starting weekly roadmap synchronization...")
        
        try:
            channel = self.get_channel(settings.DISCORD_CHANNEL_ID)
            if not channel:
                channel = await self.fetch_channel(settings.DISCORD_CHANNEL_ID)
                
            if not channel:
                logger.error(f"Could not locate channel ID {settings.DISCORD_CHANNEL_ID}")
                return

            # 1. Trigger API sync
            metadata = await self.api_client.trigger_generation()
            excel_url = metadata.get("excel_url", "Attached directly")
            
            # 2. Download generated assets
            image_bytes = await self.api_client.fetch_gantt_image()
            excel_bytes = await self.api_client.fetch_excel_file()
            
            if not image_bytes or not excel_bytes:
                raise RuntimeError("Failed to fetch generated assets from the API.")

            # 3. Compile and post Embed
            embed = discord.Embed(
                title="🗺️ UBSI Program - Weekly Roadmap Sync",
                description="The program roadmap has been synchronized with Linear. The visual chart and the Excel tracking file are attached directly to this message.",
                color=0x1B365D,
                timestamp=datetime.now(timezone.utc)
            )
            if excel_url.startswith("http"):
                embed.add_field(name="📊 Consolidated Spreadsheet", value=f"[Open Google Drive Link]({excel_url})", inline=False)
            else:
                embed.add_field(name="📊 Consolidated Spreadsheet", value="Attached directly as a file below 📁", inline=False)
                
            embed.set_image(url="attachment://roadmap.png")
            embed.set_footer(text="System status: Healthy | Automated Cron Pipeline")

            image_file = discord.File(io.BytesIO(image_bytes), filename="roadmap.png")
            excel_file = discord.File(io.BytesIO(excel_bytes), filename="Linear_Roadmap.xlsx")
            
            await channel.send(embed=embed, files=[image_file, excel_file])
            logger.info("CronJob completed successfully.")
        except Exception as e:
            logger.error(f"CronJob execution failed: {e}")
        finally:
            await self.close()

def main():
    client = CronClient()
    client.run(settings.DISCORD_TOKEN.get_secret_value())

if __name__ == "__main__":
    main()