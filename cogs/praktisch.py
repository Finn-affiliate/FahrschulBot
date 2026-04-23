import discord
from discord.ext import commands
from discord import app_commands
import logging
import os
import tempfile
from datetime import datetime

import database as db
import pdf_generator as pdf_gen
import weekly_reports as wr

logger = logging.getLogger(__name__)

FAHRLEHRER_ROLE_ID = 1419390036419412005
ARCHIV_KANAL_ID = 1473742086171001067

KATEGORIEN = ["A", "B", "C", "D", "E", "F"]
KATEGORIE_NAMES = {
    "A": "Motorrad", "B": "Auto", "C": "LKW",
    "D": "Bus", "E": "Boot", "F": "Flugzeug"
}


def has_fahrlehrer():
    async def predicate(interaction: discord.Interaction) -> bool:
        if any(r.id == FAHRLEHRER_ROLE_ID for r in interaction.user.roles):
            return True
        await interaction.response.send_message(
            "❌ Du hast keine Berechtigung für diesen Befehl.", ephemeral=True
        )
        return False
    return app_commands.check(predicate)


class SchuelerdatenModal(discord.ui.Modal, title="Schülerdaten"):
    vorname = discord.ui.TextInput(label="Vorname", placeholder="Max", max_length=50)
    nachname = discord.ui.TextInput(label="Nachname", placeholder="Mustermann", max_length=50)
    geburtsdatum = discord.ui.TextInput(label="Geburtsdatum", placeholder="01.01.2000", max_length=20)
    telefon = discord.ui.TextInput(label="Telefonnummer", placeholder="+49 123 456789", max_length=30)
    psn = discord.ui.TextInput(label="PSN / Spieler-ID", placeholder="PSN-ID", max_length=50)

    def __init__(self, schueler: discord.Member, kategorie: str, fahrlehrer: discord.Member):
        super().__init__()
        self.schueler = schueler
        self.kategorie = kategorie
        self.fahrlehrer = fahrlehrer

    async def on_submit(self, interaction: discord.Interaction):
        gestartet_am = datetime.now().strftime("%d.%m.%Y %H:%M")
        pruefung_id = db.start_praktische_pruefung(
            schueler_id=self.schueler.id,
            fahrlehrer_id=self.fahrlehrer.id,
            kategorie=self.kategorie,
            vorname=self.vorname.value,
            nachname=self.nachname.value,
            geburtsdatum=self.geburtsdatum.value,
            telefon=self.telefon.value,
            psn=self.psn.value,
            gestartet_am=gestartet_am,
        )
        await wr.ensure_fahrlehrer_channel(interaction.guild, self.fahrlehrer.display_name)

        kat_name = KATEGORIE_NAMES.get(self.kategorie.upper(), self.kategorie)
        embed = discord.Embed(
            title="✅ Prüfung gestartet",
            description=(
                f"**Schüler:** {self.schueler.mention}\n"
                f"**Kategorie:** {self.kategorie} – {kat_name}\n"
                f"**Name:** {self.vorname.value} {self.nachname.value}\n"
                f"**Prüfungs-ID:** `{pruefung_id}`"
            ),
            color=discord.Color.blue(),
            timestamp=datetime.now(),
        )
        embed.set_footer(text=f"Gestartet von {self.fahrlehrer.display_name}")
        await interaction.response.send_message(embed=embed, ephemeral=True)


class KategorieView(discord.ui.View):
    def __init__(self, schueler: discord.Member, fahrlehrer: discord.Member):
        super().__init__(timeout=120)
        self.schueler = schueler
        self.fahrlehrer = fahrlehrer
        select = discord.ui.Select(
            placeholder="Kategorie wählen...",
            options=[
                discord.SelectOption(
                    label=f"{k} – {KATEGORIE_NAMES[k]}",
                    value=k,
                    description=KATEGORIE_NAMES[k],
                )
                for k in KATEGORIEN
            ],
        )
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        kategorie = interaction.data["values"][0]
        modal = SchuelerdatenModal(self.schueler, kategorie, self.fahrlehrer)
        await interaction.response.send_modal(modal)
        self.stop()


class PruefungBeendenModal(discord.ui.Modal, title="Prüfung beenden"):
    fahrlehrername = discord.ui.TextInput(
        label="Fahrlehrername", placeholder="Dein vollständiger Name", max_length=100
    )
    unterschrift = discord.ui.TextInput(
        label="Unterschrift (Kürzel/Name)", placeholder="z.B. M. Mustermann", max_length=50
    )
    bemerkung = discord.ui.TextInput(
        label="Bemerkung (optional)", placeholder="...", required=False,
        style=discord.TextStyle.paragraph, max_length=500
    )

    def __init__(self, pruefung_id: int, bestanden: bool, schueler: discord.Member):
        super().__init__()
        self.pruefung_id = pruefung_id
        self.bestanden = bestanden
        self.schueler = schueler

    async def on_submit(self, interaction: discord.Interaction):
        datum = datetime.now().strftime("%d.%m.%Y %H:%M")

        db.finish_praktische_pruefung(
            pruefung_id=self.pruefung_id,
            bestanden=self.bestanden,
            unterschrift=self.unterschrift.value,
            bemerkung=self.bemerkung.value or "",
            datum=datum,
        )

        pruefung = db.get_pruefung_by_id(self.pruefung_id)
        pruefung["fahrlehrer_name"] = self.fahrlehrername.value
        pruefung["unterschrift"] = self.unterschrift.value

        db.increment_praktisch(
            interaction.user.id,
            interaction.user.display_name,
            pruefung["kategorie"],
            self.bestanden,
        )

        await self._handle_ergebnis(interaction, pruefung)

    async def _handle_ergebnis(self, interaction: discord.Interaction, pruefung: dict):
        await interaction.response.defer(ephemeral=True)
        kat = pruefung["kategorie"].upper()
        kat_name = KATEGORIE_NAMES.get(kat, kat)

        if self.bestanden:
            # PDF erstellen
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                pdf_path = tmp.name

            try:
                pdf_gen.build_pdf(pruefung, pdf_path)

                # PDF per DM senden
                try:
                    with open(pdf_path, "rb") as f:
                        await self.schueler.send(
                            "🎉 **Herzlichen Glückwunsch!**\n"
                            "Anbei dein Prüfungszeugnis der Washington Driving School.",
                            file=discord.File(f, filename="Pruefungszeugnis.pdf"),
                        )
                    dm_ok = True
                except discord.Forbidden:
                    dm_ok = False
            finally:
                try:
                    os.unlink(pdf_path)
                except Exception:
                    pass

            # Archiv
            archiv_embed = _build_archiv_embed(pruefung)
            archiv_kanal = interaction.guild.get_channel(ARCHIV_KANAL_ID)
            if archiv_kanal:
                try:
                    await archiv_kanal.send(embed=archiv_embed)
                except Exception as e:
                    logger.error(f"Archiv-Post fehlgeschlagen: {e}")

            status_text = "✅ Bestanden"
            color = discord.Color.green()
            dm_note = "" if dm_ok else f"\n⚠️ DM an {self.schueler.mention} nicht möglich. Bitte Zeugnis manuell aushändigen."
        else:
            status_text = "❌ Nicht bestanden"
            color = discord.Color.red()
            dm_note = ""
            try:
                await self.schueler.send(
                    "Tut uns leid, Sie haben die praktische Prüfung nicht bestanden. "
                    "Bitte melden Sie sich für einen neuen Termin."
                )
            except Exception:
                pass

        embed = discord.Embed(
            title=f"Prüfung beendet – {status_text}",
            description=(
                f"**Schüler:** {self.schueler.mention}\n"
                f"**Kategorie:** {pruefung['kategorie']} – {kat_name}\n"
                f"**Name:** {pruefung['vorname']} {pruefung['nachname']}\n"
                f"**Fahrlehrer:** {pruefung['fahrlehrer_name']}\n"
                f"**Ergebnis:** {status_text}"
            ),
            color=color,
            timestamp=datetime.now(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)
        if dm_note:
            await interaction.followup.send(dm_note, ephemeral=True)


def _build_archiv_embed(pruefung: dict) -> discord.Embed:
    kat = pruefung["kategorie"].upper()
    kat_name = KATEGORIE_NAMES.get(kat, kat)
    embed = discord.Embed(
        title="✅ Praktische Prüfung Bestanden",
        color=discord.Color.green(),
        timestamp=datetime.now(),
    )
    embed.add_field(name="Kategorie", value=f"{kat} – {kat_name}", inline=True)
    embed.add_field(name="Vorname", value=pruefung.get("vorname", ""), inline=True)
    embed.add_field(name="Nachname", value=pruefung.get("nachname", ""), inline=True)
    embed.add_field(name="Geburtsdatum", value=pruefung.get("geburtsdatum", ""), inline=True)
    embed.add_field(name="Telefon", value=pruefung.get("telefon", ""), inline=True)
    embed.add_field(name="PSN", value=pruefung.get("psn", ""), inline=True)
    embed.add_field(name="Fahrlehrer", value=pruefung.get("fahrlehrer_name", ""), inline=True)
    embed.add_field(name="Unterschrift", value=pruefung.get("unterschrift", ""), inline=True)
    embed.add_field(name="Datum", value=pruefung.get("datum", ""), inline=True)
    if pruefung.get("bemerkung"):
        embed.add_field(name="Bemerkung", value=pruefung["bemerkung"], inline=False)
    embed.set_footer(text="Washington Driving School | Archiv")
    return embed


class ErgebnisView(discord.ui.View):
    def __init__(self, pruefung_id: int, schueler: discord.Member):
        super().__init__(timeout=120)
        self.pruefung_id = pruefung_id
        self.schueler = schueler

    @discord.ui.button(label="✅ Bestanden", style=discord.ButtonStyle.success)
    async def bestanden(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PruefungBeendenModal(self.pruefung_id, True, self.schueler)
        await interaction.response.send_modal(modal)
        self.stop()

    @discord.ui.button(label="❌ Nicht bestanden", style=discord.ButtonStyle.danger)
    async def nicht_bestanden(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = PruefungBeendenModal(self.pruefung_id, False, self.schueler)
        await interaction.response.send_modal(modal)
        self.stop()


class PruefungSelectView(discord.ui.View):
    def __init__(self, pruefungen: list[dict], guild: discord.Guild):
        super().__init__(timeout=120)
        self.guild = guild
        options = []
        for p in pruefungen[:25]:
            schueler = guild.get_member(p["schueler_id"])
            name = schueler.display_name if schueler else str(p["schueler_id"])
            kat_name = KATEGORIE_NAMES.get(p["kategorie"].upper(), p["kategorie"])
            options.append(discord.SelectOption(
                label=f"{name} – {p['kategorie']} ({kat_name})",
                value=str(p["id"]),
                description=f"Gestartet: {p['gestartet_am']}",
            ))
        select = discord.ui.Select(placeholder="Prüfung auswählen...", options=options)
        select.callback = self.select_callback
        self.add_item(select)

    async def select_callback(self, interaction: discord.Interaction):
        pruefung_id = int(interaction.data["values"][0])
        pruefung = db.get_pruefung_by_id(pruefung_id)
        schueler = self.guild.get_member(pruefung["schueler_id"])
        if schueler is None:
            await interaction.response.send_message("❌ Schüler nicht mehr auf dem Server.", ephemeral=True)
            return
        view = ErgebnisView(pruefung_id, schueler)
        await interaction.response.send_message("Ergebnis wählen:", view=view, ephemeral=True)
        self.stop()


pruefung_group = app_commands.Group(name="prüfung", description="Prüfungsverwaltung")


class PraktischCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @pruefung_group.command(name="starten", description="Startet eine praktische Prüfung.")
    @app_commands.describe(schueler="Der Fahrschüler")
    @has_fahrlehrer()
    async def pruefung_starten(self, interaction: discord.Interaction, schueler: discord.Member):
        view = KategorieView(schueler, interaction.user)
        await interaction.response.send_message(
            f"Kategorie für **{schueler.display_name}** wählen:", view=view, ephemeral=True
        )

    @pruefung_group.command(name="beenden", description="Beendet eine laufende Prüfung.")
    @has_fahrlehrer()
    async def pruefung_beenden(self, interaction: discord.Interaction):
        pruefungen = db.get_laufende_pruefungen(interaction.user.id)
        if not pruefungen:
            await interaction.response.send_message(
                "❌ Du hast keine laufenden Prüfungen.", ephemeral=True
            )
            return

        if len(pruefungen) == 1:
            p = pruefungen[0]
            schueler = interaction.guild.get_member(p["schueler_id"])
            if schueler is None:
                await interaction.response.send_message(
                    "❌ Schüler nicht mehr auf dem Server.", ephemeral=True
                )
                return
            view = ErgebnisView(p["id"], schueler)
            kat_name = KATEGORIE_NAMES.get(p["kategorie"].upper(), p["kategorie"])
            await interaction.response.send_message(
                f"Ergebnis für **{schueler.display_name}** ({p['kategorie']} – {kat_name}):",
                view=view,
                ephemeral=True,
            )
        else:
            view = PruefungSelectView(pruefungen, interaction.guild)
            await interaction.response.send_message(
                "Welche Prüfung möchtest du beenden?", view=view, ephemeral=True
            )

    def get_app_commands(self):
        return [pruefung_group]


async def setup(bot: commands.Bot):
    cog = PraktischCog(bot)
    bot.tree.add_command(pruefung_group)
    await bot.add_cog(cog)
