import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import string
import logging
from datetime import datetime

import database as db
import weekly_reports as wr

logger = logging.getLogger(__name__)

FAHRLEHRER_ROLE_ID = 1419390036419412005
THEORIE_ROLE_ID = 1467931970158985395
FRAGEN_PATH = "fragen.json"
FRAGEN_PRO_PRUEFUNG = 20
MIN_RICHTIG = 18


def load_fragen() -> list[dict]:
    try:
        with open(FRAGEN_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"{FRAGEN_PATH} nicht gefunden!")
        return []


def generate_password(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


def has_fahrlehrer():
    async def predicate(interaction: discord.Interaction) -> bool:
        if any(r.id == FAHRLEHRER_ROLE_ID for r in interaction.user.roles):
            return True
        await interaction.response.send_message(
            "❌ Du hast keine Berechtigung für diesen Befehl.", ephemeral=True
        )
        return False
    return app_commands.check(predicate)


class FrageView(discord.ui.View):
    def __init__(self, fragen: list[dict], schueler: discord.Member, fahrlehrer_id: int):
        super().__init__(timeout=600)
        self.fragen = fragen
        self.schueler = schueler
        self.fahrlehrer_id = fahrlehrer_id
        self.aktuell = 0
        self.richtig = 0
        self.message: discord.Message = None

    def build_embed(self) -> discord.Embed:
        if self.aktuell >= len(self.fragen):
            return None
        frage = self.fragen[self.aktuell]
        embed = discord.Embed(
            title=f"Theorieprüfung – Frage {self.aktuell + 1}/{len(self.fragen)}",
            description=f"**{frage['frage']}**",
            color=discord.Color.blurple(),
        )
        for opt in ["A", "B", "C", "D"]:
            embed.add_field(name=opt, value=frage.get(opt, ""), inline=False)
        embed.set_footer(text=f"Bisher richtig: {self.richtig}")
        return embed

    def update_buttons(self):
        self.clear_items()
        for opt in ["A", "B", "C", "D"]:
            btn = discord.ui.Button(
                label=opt, style=discord.ButtonStyle.secondary, custom_id=f"antwort_{opt}"
            )
            btn.callback = self.make_callback(opt)
            self.add_item(btn)

    def make_callback(self, opt: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.schueler.id:
                await interaction.response.send_message(
                    "Diese Prüfung gehört dir nicht.", ephemeral=True
                )
                return

            frage = self.fragen[self.aktuell]
            if frage["richtig"].upper() == opt.upper():
                self.richtig += 1

            self.aktuell += 1

            if self.aktuell >= len(self.fragen):
                await self.finish(interaction)
            else:
                self.update_buttons()
                await interaction.response.edit_message(
                    embed=self.build_embed(), view=self
                )
        return callback

    async def finish(self, interaction: discord.Interaction):
        bestanden = self.richtig >= MIN_RICHTIG
        datum = datetime.now().strftime("%d.%m.%Y %H:%M")

        db.save_theorie_pruefung(
            self.schueler.id, self.fahrlehrer_id,
            self.richtig, bestanden, datum
        )

        if bestanden:
            # Rolle vergeben
            theorie_role = interaction.guild.get_role(THEORIE_ROLE_ID)
            if theorie_role is None:
                theorie_role = await interaction.guild.create_role(
                    name="Theorieprüfung",
                    color=discord.Color.green(),
                    reason="Automatisch erstellt durch Fahrschul-Bot",
                )
            try:
                await self.schueler.add_roles(theorie_role, reason="Theorieprüfung bestanden")
            except Exception as e:
                logger.error(f"Rolle konnte nicht vergeben werden: {e}")

            embed = discord.Embed(
                title="🎉 Theorieprüfung bestanden!",
                description=f"**{self.schueler.display_name}** hat {self.richtig}/{len(self.fragen)} Fragen richtig beantwortet.",
                color=discord.Color.green(),
            )
            try:
                await self.schueler.send("✅ Herzlichen Glückwunsch! Du hast die Theorieprüfung bestanden.")
            except Exception:
                pass
        else:
            embed = discord.Embed(
                title="❌ Theorieprüfung nicht bestanden",
                description=f"**{self.schueler.display_name}** hat {self.richtig}/{len(self.fragen)} Fragen richtig beantwortet.\nMindest: {MIN_RICHTIG}/{len(self.fragen)}",
                color=discord.Color.red(),
            )
            try:
                await self.schueler.send(
                    "Tut uns leid, Sie haben die Theorieprüfung nicht bestanden. "
                    "Bitte melden Sie sich für eine neue Freischaltung."
                )
            except Exception:
                pass

        self.stop()
        await interaction.response.edit_message(embed=embed, view=None)


class TheorieCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    passwort_group = app_commands.Group(name="passwort", description="Passwort-Verwaltung")

    @passwort_group.command(name="erstellen", description="Erstellt ein Theorie-Passwort für einen Schüler.")
    @app_commands.describe(schueler="Der Fahrschüler")
    @has_fahrlehrer()
    async def passwort_erstellen(self, interaction: discord.Interaction, schueler: discord.Member):
        await interaction.response.defer(ephemeral=True)

        passwort = generate_password()
        datum = datetime.now().strftime("%d.%m.%Y %H:%M")

        try:
            db.create_freigabe(schueler.id, interaction.user.id, passwort, datum)
        except Exception as e:
            await interaction.followup.send(f"❌ Datenbankfehler: {e}", ephemeral=True)
            return

        db.increment_theorie_freischaltung(
            interaction.user.id, interaction.user.display_name
        )

        # Wochenbericht-Kanal sicherstellen
        await wr.ensure_fahrlehrer_channel(interaction.guild, interaction.user.display_name)

        try:
            await schueler.send(
                f"🔑 **Dein Theorie-Passwort:**\n`{passwort}`\n\n"
                f"Nutze `/theorie` und gib dieses Passwort ein, um deine Prüfung zu starten.\n"
                f"Das Passwort ist **einmalig** verwendbar."
            )
            dm_status = "✅ Passwort per DM gesendet."
        except discord.Forbidden:
            dm_status = f"⚠️ DM nicht möglich. Passwort: `{passwort}`"

        await interaction.followup.send(
            f"Passwort für **{schueler.display_name}** erstellt.\n{dm_status}",
            ephemeral=True,
        )

    @app_commands.command(name="theorie", description="Starte die Theorieprüfung mit deinem Passwort.")
    @app_commands.describe(passwort="Dein Theorie-Passwort")
    async def theorie(self, interaction: discord.Interaction, passwort: str):
        await interaction.response.defer(ephemeral=True)

        freigabe = db.get_freigabe_by_passwort(passwort)
        if freigabe is None:
            await interaction.followup.send(
                "❌ Ungültiges oder bereits verwendetes Passwort.", ephemeral=True
            )
            return

        if freigabe["schueler_id"] != interaction.user.id:
            await interaction.followup.send(
                "❌ Dieses Passwort gehört nicht zu deinem Account.", ephemeral=True
            )
            return

        alle_fragen = load_fragen()
        if len(alle_fragen) < FRAGEN_PRO_PRUEFUNG:
            await interaction.followup.send(
                f"❌ Nicht genug Fragen in der Datenbank ({len(alle_fragen)}/{FRAGEN_PRO_PRUEFUNG}).",
                ephemeral=True,
            )
            return

        db.mark_freigabe_genutzt(passwort)

        ausgewaehlte = random.sample(alle_fragen, FRAGEN_PRO_PRUEFUNG)
        random.shuffle(ausgewaehlte)

        view = FrageView(ausgewaehlte, interaction.user, freigabe["fahrlehrer_id"])
        view.update_buttons()
        embed = view.build_embed()

        msg = await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        view.message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(TheorieCog(bot))
