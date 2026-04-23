import discord
import logging
from datetime import datetime, timedelta

import database as db

logger = logging.getLogger(__name__)

WOCHENBERICHT_KATEGORIE_ID = 1419390038038544610
KATEGORIE_NAMES = {
    "a": "Motorrad", "b": "Auto", "c": "LKW",
    "d": "Bus", "e": "Boot", "f": "Flugzeug"
}


async def ensure_fahrlehrer_channel(guild: discord.Guild, fahrlehrer_name: str) -> discord.TextChannel:
    """Erstellt den Berichtskanal für einen Fahrlehrer falls er nicht existiert."""
    category = guild.get_channel(WOCHENBERICHT_KATEGORIE_ID)
    if category is None:
        logger.error(f"Wochenbericht-Kategorie {WOCHENBERICHT_KATEGORIE_ID} nicht gefunden.")
        return None

    channel_name = f"bericht-{fahrlehrer_name.lower().replace(' ', '-')}"
    existing = discord.utils.get(category.channels, name=channel_name)
    if existing:
        return existing

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            topic=f"Wochenbericht für Fahrlehrer {fahrlehrer_name}",
        )
        logger.info(f"Berichtskanal erstellt: {channel_name}")
        return channel
    except Exception as e:
        logger.error(f"Fehler beim Erstellen des Berichtskanals: {e}")
        return None


def build_wochenbericht_embed(stats: dict, woche_start: str) -> discord.Embed:
    """Erstellt das Embed für den Wochenbericht."""
    woche_end_dt = datetime.strptime(woche_start, "%Y-%m-%d") + timedelta(days=6)
    woche_end = woche_end_dt.strftime("%d.%m.%Y")
    woche_start_fmt = datetime.strptime(woche_start, "%Y-%m-%d").strftime("%d.%m.%Y")

    embed = discord.Embed(
        title="📊 Wochenbericht",
        description=f"**Washington Driving School**\n{woche_start_fmt} – {woche_end}",
        color=discord.Color.from_rgb(26, 26, 46),
        timestamp=datetime.now(),
    )
    embed.set_footer(text="Washington Driving School | Automatischer Wochenbericht")

    embed.add_field(
        name="👤 Fahrlehrer",
        value=stats.get("fahrlehrer_name", "Unbekannt"),
        inline=False,
    )
    embed.add_field(
        name="📚 Theorie-Freischaltungen",
        value=str(stats.get("theorie_freischaltungen", 0)),
        inline=True,
    )

    praktisch_lines = []
    for key, label in KATEGORIE_NAMES.items():
        val = stats.get(f"praktisch_{key}", 0)
        praktisch_lines.append(f"**{key.upper()} ({label}):** {val}")

    embed.add_field(
        name="🚗 Praktische Prüfungen",
        value="\n".join(praktisch_lines) or "–",
        inline=False,
    )
    embed.add_field(
        name="✅ Bestanden",
        value=str(stats.get("bestanden", 0)),
        inline=True,
    )
    embed.add_field(
        name="❌ Nicht bestanden",
        value=str(stats.get("nicht_bestanden", 0)),
        inline=True,
    )
    return embed


async def send_weekly_reports(guild: discord.Guild):
    """Sendet Wochenberichte für alle Fahrlehrer."""
    woche_start = db.get_current_week_start()
    alle_stats = db.get_all_fahrlehrer_stats_week(woche_start)

    if not alle_stats:
        logger.info("Keine Statistikdaten für diese Woche gefunden.")
        return

    for stats in alle_stats:
        fahrlehrer_name = stats.get("fahrlehrer_name", "Unbekannt")
        channel = await ensure_fahrlehrer_channel(guild, fahrlehrer_name)
        if channel is None:
            continue

        embed = build_wochenbericht_embed(stats, woche_start)
        try:
            await channel.send(embed=embed)
            logger.info(f"Wochenbericht gesendet für {fahrlehrer_name}.")
        except Exception as e:
            logger.error(f"Fehler beim Senden des Wochenberichts für {fahrlehrer_name}: {e}")
