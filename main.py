import discord
from discord.ext import commands
import logging
import sys
import asyncio

from config import BOT_TOKEN_FAHRSCHULE
import database as db

# Logging konfigurieren
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("fahrschule.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

SERVER_ID = 1419390036419411998
FAHRLEHRER_ROLE_ID = 1419390036419412005
ADMIN_ROLE_ID = 1419390036511559709
THEORIE_ROLE_ID = 1467931970158985395

COGS = [
    "cogs.theorie",
    "cogs.praktisch",
    "cogs.statistik",
    "cogs.fragen",
    "cogs.wochenbericht",
]

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class FahrschulBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        db.init_db()
        for cog in COGS:
            try:
                await self.load_extension(cog)
                logger.info(f"Cog geladen: {cog}")
            except Exception as e:
                logger.error(f"Fehler beim Laden von {cog}: {e}", exc_info=True)

        guild = discord.Object(id=SERVER_ID)
        self.tree.copy_global_to(guild=guild)
        synced = await self.tree.sync(guild=guild)
        logger.info(f"Slash Commands synchronisiert: {len(synced)} Commands.")

    async def on_ready(self):
        logger.info(f"Bot eingeloggt als {self.user} (ID: {self.user.id})")
        await self._ensure_roles()
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Washington Driving School",
            )
        )

    async def _ensure_roles(self):
        guild = self.get_guild(SERVER_ID)
        if guild is None:
            return

        role_configs = [
            (FAHRLEHRER_ROLE_ID, "Fahrlehrer", discord.Color.blue()),
            (ADMIN_ROLE_ID, "Admin", discord.Color.red()),
            (THEORIE_ROLE_ID, "Theorieprüfung", discord.Color.green()),
        ]

        for role_id, name, color in role_configs:
            if guild.get_role(role_id) is None:
                try:
                    await guild.create_role(
                        name=name,
                        color=color,
                        reason=f"Automatisch erstellt durch Fahrschul-Bot (fehlende Rolle {role_id})",
                    )
                    logger.info(f"Rolle erstellt: {name}")
                except Exception as e:
                    logger.error(f"Rolle '{name}' konnte nicht erstellt werden: {e}")

    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception):
        if isinstance(error, app_commands.CheckFailure):
            return  # Bereits in den Checks behandelt
        logger.error(f"Slash Command Fehler: {error}", exc_info=True)
        msg = "❌ Ein unerwarteter Fehler ist aufgetreten."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(msg, ephemeral=True)
            else:
                await interaction.response.send_message(msg, ephemeral=True)
        except Exception:
            pass


bot = FahrschulBot()


if __name__ == "__main__":
    bot.run(BOT_TOKEN_FAHRSCHULE, log_handler=None)
