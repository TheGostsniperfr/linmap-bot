import logging
import io
import discord
from discord.ext import commands, tasks
from datetime import datetime, timezone
from typing import Optional

from src.config import settings
from src.bot.api_client import LinmapAPIClient

logger = logging.getLogger("linmap-bot")

class LinmapBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.api_client = LinmapAPIClient()

    async def setup_hook(self) -> None:
        """Pre-activation lifecycle hook for sync and task registration."""
        self.weekly_roadmap_sync.start()
        logger.info("Background task scheduler initialized.")

    async def on_ready(self) -> None:
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        try:
            # Sync application slash commands globally
            synced = await self.tree.sync()
            logger.info(f"Successfully synchronized {len(synced)} slash commands globally.")
        except Exception as e:
            logger.error(f"Slash command synchronization failed: {e}")

    @tasks.loop(hours=168) # 7 Days
    async def weekly_roadmap_sync(self) -> None:
        """Automated weekly background task loop."""
        logger.info("Executing scheduled weekly roadmap synchronization...")
        channel = self.get_channel(settings.DISCORD_CHANNEL_ID)
        if not channel:
            logger.warning(f"Could not locate channel ID {settings.DISCORD_CHANNEL_ID} to post updates.")
            return
            
        try:
            # Weekly automation runs without zoom (complete view)
            await self._run_pipeline_and_post(channel)
        except Exception as e:
            logger.error(f"Weekly scheduled generation failed: {e}")

    @weekly_roadmap_sync.before_loop
    async def before_weekly_sync(self):
        await self.wait_until_ready()

    async def _run_pipeline_and_post(self, channel: discord.abc.Messageable, months: Optional[int] = None) -> None:
        """Executes API generation, downloads assets, and publishes rich Embed on Discord."""
        # 1. Trigger the sync on FastAPI Pod (passes the temporal zoom parameter)
        metadata = await self.api_client.trigger_generation(months=months)
        excel_url = metadata.get("excel_url", "Attached directly")
        
        # 2. Download generated Gantt Image
        image_bytes = await self.api_client.fetch_gantt_image()
        if not image_bytes:
            raise RuntimeError("Failed to fetch rendered Gantt chart image from the API.")

        # 3. Download generated Excel Spreadsheet
        excel_bytes = await self.api_client.fetch_excel_file()
        if not excel_bytes:
            raise RuntimeError("Failed to fetch Excel report from the API.")

        # 4. Compile Embed
        title_suffix = f" - Zoom {months} mois 🔍" if months else ""
        embed = discord.Embed(
            title=f"🗺️ UBSI Program - Roadmap Sync{title_suffix}",
            description="The program roadmap has been synchronized with Linear. The visual chart and the Excel tracking file are attached directly to this message.",
            color=0x1B365D,
            timestamp=datetime.now(timezone.utc)
        )
        
        if excel_url.startswith("http"):
            embed.add_field(name="📊 Consolidated Spreadsheet", value=f"[Open Google Drive Link]({excel_url})", inline=False)
        else:
            embed.add_field(name="📊 Consolidated Spreadsheet", value="Attached directly as a file below 📁", inline=False)
            
        embed.set_image(url="attachment://roadmap.png")
        embed.set_footer(text="System status: Healthy | Automated Pipeline")

        # 5. Attach files in-memory
        image_file = discord.File(io.BytesIO(image_bytes), filename="roadmap.png")
        excel_file = discord.File(io.BytesIO(excel_bytes), filename="Linear_Roadmap.xlsx")
        
        # 6. Broadcast to target channel with both files
        await channel.send(embed=embed, files=[image_file, excel_file])


# Instantiate the bot inside global scope
bot = LinmapBot()


@bot.tree.command(name="roadmap", description="Generates the complete roadmap encompassing all projects.")
async def manual_roadmap(interaction: discord.Interaction) -> None:
    """Manual trigger interaction with deferral mechanism."""
    # Defer to prevent Discord interaction token expiration timeout (3-second limit)
    await interaction.response.defer(ephemeral=False)
    
    try:
        await bot._run_pipeline_and_post(interaction.channel)
        await interaction.followup.send("Roadmap complète rafraîchie et postée ci-dessous ! 🚀", ephemeral=True)
    except Exception as e:
        logger.error(f"Manual generation command failed: {e}")
        await interaction.followup.send(f"❌ La synchronisation a échoué : {e}", ephemeral=True)


@bot.tree.command(name="roadmap_zoom", description="Generates a short-term roadmap starting today for a defined number of months.")
@discord.app_commands.describe(months="The number of months to display starting today (e.g. 1, 2, 3...)")
async def manual_roadmap_zoom(interaction: discord.Interaction, months: int) -> None:
    """Manual trigger with temporal zoom parameter."""
    if months < 1 or months > 12:
        await interaction.response.send_message("❌ Le nombre de mois doit être compris entre 1 et 12.", ephemeral=True)
        return

    # Defer to prevent Discord interaction token expiration timeout (3-second limit)
    await interaction.response.defer(ephemeral=False)
    
    try:
        # Call the pipeline with the months constraint
        await bot._run_pipeline_and_post(interaction.channel, months=months)
        await interaction.followup.send(f"Roadmap zoomée sur {months} mois rafraîchie et postée ci-dessous ! 🔍", ephemeral=True)
    except Exception as e:
        logger.error(f"Zoomed manual generation command failed: {e}")
        await interaction.followup.send(f"❌ La synchronisation de la roadmap zoomée a échoué : {e}", ephemeral=True)


def main() -> None:
    """Direct entrypoint for starting the Discord Client worker."""
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting Discord Client Worker...")
    bot.run(settings.DISCORD_TOKEN.get_secret_value())

if __name__ == "__main__":
    main()