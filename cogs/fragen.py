import discord
from discord.ext import commands
from discord import app_commands
import json
import logging

logger = logging.getLogger(__name__)

ADMIN_ROLE_ID = 1419390036511559709
FRAGEN_PATH = "fragen.json"


def load_fragen() -> list[dict]:
    try:
        with open(FRAGEN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def save_fragen(fragen: list[dict]):
    with open(FRAGEN_PATH, "w", encoding="utf-8") as f:
        json.dump(fragen, f, ensure_ascii=False, indent=2)


def has_admin():
    async def predicate(interaction: discord.Interaction) -> bool:
        if any(r.id == ADMIN_ROLE_ID for r in interaction.user.roles):
            return True
        await interaction.response.send_message(
            "❌ Du brauchst Admin-Rechte.", ephemeral=True
        )
        return False
    return app_commands.check(predicate)


class FrageHinzufuegenModal(discord.ui.Modal, title="Frage hinzufügen"):
    frage = discord.ui.TextInput(label="Frage", style=discord.TextStyle.paragraph, max_length=500)
    antwort_a = discord.ui.TextInput(label="Antwort A", max_length=200)
    antwort_b = discord.ui.TextInput(label="Antwort B", max_length=200)
    antwort_c = discord.ui.TextInput(label="Antwort C", max_length=200)
    antwort_d = discord.ui.TextInput(label="Antwort D", max_length=200)

    def __init__(self, richtig: str):
        super().__init__()
        self.richtig = richtig.upper()

    async def on_submit(self, interaction: discord.Interaction):
        fragen = load_fragen()
        neue_frage = {
            "frage": self.frage.value,
            "A": self.antwort_a.value,
            "B": self.antwort_b.value,
            "C": self.antwort_c.value,
            "D": self.antwort_d.value,
            "richtig": self.richtig,
        }
        fragen.append(neue_frage)
        save_fragen(fragen)
        await interaction.response.send_message(
            f"✅ Frage hinzugefügt. Gesamt: **{len(fragen)}** Fragen.", ephemeral=True
        )


class FragenCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # Gruppe als Klassen-Attribut – discord.py blendet self korrekt aus
    frage_group = app_commands.Group(name="frage", description="Fragen-Verwaltung")

    @frage_group.command(name="hinzufügen", description="Fügt eine neue Theoriefrage hinzu.")
    @app_commands.describe(richtig="Die richtige Antwort (A, B, C oder D)")
    @app_commands.choices(richtig=[
        app_commands.Choice(name="A", value="A"),
        app_commands.Choice(name="B", value="B"),
        app_commands.Choice(name="C", value="C"),
        app_commands.Choice(name="D", value="D"),
    ])
    @has_admin()
    async def frage_hinzufuegen(self, interaction: discord.Interaction, richtig: str):
        modal = FrageHinzufuegenModal(richtig)
        await interaction.response.send_modal(modal)

    @frage_group.command(name="löschen", description="Löscht eine Frage anhand ihrer Nummer.")
    @app_commands.describe(nummer="Die Fragenummer (1-basiert)")
    @has_admin()
    async def frage_loeschen(self, interaction: discord.Interaction, nummer: int):
        fragen = load_fragen()
        if nummer < 1 or nummer > len(fragen):
            await interaction.response.send_message(
                f"❌ Ungültige Nummer. Es gibt {len(fragen)} Fragen.", ephemeral=True
            )
            return
        removed = fragen.pop(nummer - 1)
        save_fragen(fragen)
        await interaction.response.send_message(
            f"✅ Frage #{nummer} gelöscht: *{removed['frage'][:60]}...*\nNoch {len(fragen)} Fragen.",
            ephemeral=True,
        )

    @frage_group.command(name="anzeigen", description="Zeigt alle Fragen an.")
    @has_admin()
    async def fragen_anzeigen(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        fragen = load_fragen()
        if not fragen:
            await interaction.followup.send("Keine Fragen vorhanden.", ephemeral=True)
            return

        chunks = []
        current = []
        for i, f in enumerate(fragen, 1):
            line = f"**#{i}** {f['frage'][:80]} *(Richtig: {f['richtig']})*"
            current.append(line)
            if len(current) >= 10:
                chunks.append(current)
                current = []
        if current:
            chunks.append(current)

        for idx, chunk in enumerate(chunks):
            embed = discord.Embed(
                title=f"Fragen ({idx * 10 + 1}–{idx * 10 + len(chunk)}) / {len(fragen)} gesamt",
                description="\n".join(chunk),
                color=discord.Color.blue(),
            )
            await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(FragenCog(bot))
