import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from datetime import datetime, time, timezone

import weekly_reports as wr

logger = logging.getLogger(__name__)

ADMIN_ROLE_ID = 1419390036511559709
SERVER_ID = 1419390036419411998

# Sonntag 23:59 UTC
WOCHENBERICHT_ZEIT = time(hour=22, minute=59, tzinfo=timezone.utc)


def has_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            return True
        await interaction.response.send_message(
            "❌ Du brauchst Admin-Rechte.", ephemeral=True
        )
        return False
    return app_commands.check(predicate)


class WochenberichtCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.wochenbericht_task.start()

    def cog_unload(self):
        self.wochenbericht_task.cancel()

    @tasks.loop(time=WOCHENBERICHT_ZEIT)
    async def wochenbericht_task(self):
        # Nur sonntags ausführen (weekday 6 = Sonntag)
        if datetime.now().weekday() != 6:
            return

        guild = self.bot.get_guild(SERVER_ID)
        if guild is None:
            logger.error(f"Guild {SERVER_ID} nicht gefunden für Wochenbericht.")
            return

        logger.info("Starte automatischen Wochenbericht...")
        await wr.send_weekly_reports(guild)

    @wochenbericht_task.before_loop
    async def before_wochenbericht(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="wochenbericht", description="Löst den Wochenbericht sofort aus.")
    @has_admin()
    async def wochenbericht_jetzt(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await wr.send_weekly_reports(interaction.guild)
        await interaction.followup.send("✅ Wochenbericht wurde gesendet.", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(WochenberichtCog(bot))
