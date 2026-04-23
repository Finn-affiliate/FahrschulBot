import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import logging

import database as db

logger = logging.getLogger(__name__)

FAHRLEHRER_ROLE_ID = 1419390036419412005
ADMIN_ROLE_ID = 1419390036511559709

KATEGORIE_NAMES = {
    "a": "Motorrad", "b": "Auto", "c": "LKW",
    "d": "Bus", "e": "Boot", "f": "Flugzeug"
}


def has_fahrlehrer_or_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        allowed = {FAHRLEHRER_ROLE_ID, ADMIN_ROLE_ID}
        if any(r.id in allowed for r in interaction.user.roles):
            return True
        await interaction.response.send_message(
            "❌ Du hast keine Berechtigung für diesen Befehl.", ephemeral=True
        )
        return False
    return app_commands.check(predicate)


class StatistikCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="statistik", description="Zeigt die Gesamtstatistik der Fahrschule.")
    @has_fahrlehrer_or_admin()
    async def statistik(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        stats = db.get_gesamtstatistik()

        embed = discord.Embed(
            title="📊 Washington Driving School – Gesamtstatistik",
            color=discord.Color.from_rgb(26, 26, 46),
            timestamp=datetime.now(),
        )
        embed.add_field(
            name="📚 Theorie-Freischaltungen",
            value=str(stats.get("theorie") or 0),
            inline=False,
        )

        praktisch_lines = []
        for key, label in KATEGORIE_NAMES.items():
            val = stats.get(key) or 0
            praktisch_lines.append(f"**{key.upper()} ({label}):** {val}")

        embed.add_field(
            name="🚗 Praktische Prüfungen",
            value="\n".join(praktisch_lines),
            inline=False,
        )
        embed.add_field(
            name="✅ Bestanden gesamt",
            value=str(stats.get("bestanden") or 0),
            inline=True,
        )
        embed.add_field(
            name="❌ Nicht bestanden gesamt",
            value=str(stats.get("nicht_bestanden") or 0),
            inline=True,
        )
        embed.set_footer(text="Washington Driving School | Statistik")

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(StatistikCog(bot))
