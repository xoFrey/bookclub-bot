import discord
from discord.ext import commands, tasks
from datetime import date, datetime, timedelta
import pytz
import database as db

BERLIN = pytz.timezone("Europe/Berlin")

STERNE_OPTIONEN = [
    discord.SelectOption(label="⭐ 1.0 – Sehr schlecht", value="1.0"),
    discord.SelectOption(label="⭐ 1.5", value="1.5"),
    discord.SelectOption(label="⭐⭐ 2.0 – Schlecht", value="2.0"),
    discord.SelectOption(label="⭐⭐ 2.5", value="2.5"),
    discord.SelectOption(label="⭐⭐⭐ 3.0 – Okay", value="3.0"),
    discord.SelectOption(label="⭐⭐⭐ 3.5", value="3.5"),
    discord.SelectOption(label="⭐⭐⭐⭐ 4.0 – Gut", value="4.0"),
    discord.SelectOption(label="⭐⭐⭐⭐ 4.5", value="4.5"),
    discord.SelectOption(label="⭐⭐⭐⭐⭐ 5.0 – Ausgezeichnet", value="5.0"),
]

def sterne_anzeige(avg):
    voll = int(avg)
    halb = 1 if (avg - voll) >= 0.5 else 0
    return "⭐" * voll + ("✨" if halb else "") + f" ({avg:.1f})"


class BewertungSelect(discord.ui.Select):
    def __init__(self, buch_id: int):
        self.buch_id = buch_id
        super().__init__(
            placeholder="Deine Bewertung...",
            options=STERNE_OPTIONEN,
            min_values=1,
            max_values=1,
            custom_id=f"bewertung_{buch_id}"
        )

    async def callback(self, interaction: discord.Interaction):
        sterne = float(self.values[0])
        gespeichert = await db.bewertung_speichern(self.buch_id, interaction.user.id, sterne)
        if gespeichert:
            await interaction.response.send_message(
                f"✅ Deine Bewertung von **{sterne} ⭐** wurde gespeichert!", ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Fehler beim Speichern.", ephemeral=True)


class BewertungView(discord.ui.View):
    def __init__(self, buch_id: int):
        super().__init__(timeout=86400)  # 24 Stunden
        self.buch_id = buch_id
        self.add_item(BewertungSelect(buch_id))

    async def on_timeout(self):
        # Bewertung schließen und Ergebnis posten
        buch = await db.buch_by_id(self.buch_id)
        if not buch or not buch['bewertung_offen']:
            return

        avg, count = await db.buch_bewertungen(self.buch_id)

        # View deaktivieren
        for item in self.children:
            item.disabled = True

        # Kanal und Nachricht finden
        # Diese werden beim Start gesetzt (siehe unten)


class Bewertung(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.aktive_bewertungen = {}  # buch_id -> (message, view)
        self.check_bewertungen.start()

    def cog_unload(self):
        self.check_bewertungen.cancel()

    @tasks.loop(minutes=1)
    async def check_bewertungen(self):
        jetzt_berlin = datetime.now(BERLIN)
        heute = jetzt_berlin.date()

        # Nur um 16:00 Uhr auslösen (innerhalb der aktuellen Minute)
        if jetzt_berlin.hour != 16 or jetzt_berlin.minute != 0:
            return

        buecher = await db.buecher_fuer_bewertung_heute(heute)
        for buch in buecher:
            await self.bewertung_starten(buch)

    async def bewertung_starten(self, buch):
        # Ersten verfügbaren Textkanal im ersten Server suchen
        for guild in self.bot.guilds:
            kanal = None
            for ch in guild.text_channels:
                if ch.permissions_for(guild.me).send_messages:
                    kanal = ch
                    break
            if not kanal:
                continue

            embed = discord.Embed(
                title="📚 Buchbewertung!",
                description=(
                    f"**{buch['titel']}** von *{buch['autor']}* wurde heute fertig gelesen!\n\n"
                    f"Ihr habt **24 Stunden** Zeit, eine Bewertung abzugeben. 🕓"
                ),
                color=discord.Color.orange()
            )
            embed.add_field(name="📅 Zeitraum", value=f"{buch['start_datum'].strftime('%d.%m.%Y')} – {buch['end_datum'].strftime('%d.%m.%Y')}", inline=True)
            embed.add_field(name="🏷️ Genre", value=buch['genre'], inline=True)

            view = BewertungView(buch['id'])
            msg = await kanal.send(embed=embed, view=view)

            # Nachricht-ID und Kanal für späteres Abschließen speichern
            await db.bewertung_schliessen_vorbereiten(buch['id'], msg.id, kanal.id)
            self.aktive_bewertungen[buch['id']] = (msg, view, kanal)

            # Nach 24h Ergebnis posten
            self.bot.loop.call_later(86400, lambda b=buch, k=kanal: self.bot.loop.create_task(self.bewertung_abschliessen(b, k)))

    async def bewertung_abschliessen(self, buch, kanal):
        avg, count = await db.buch_bewertungen(buch['id'])
        await db.bewertung_schliessen(buch['id'], None, None)

        embed = discord.Embed(
            title="📊 Bewertungsergebnis",
            description=f"Die Bewertungsphase für **{buch['titel']}** ist abgeschlossen!",
            color=discord.Color.green()
        )
        embed.add_field(name="📖 Buch", value=f"{buch['titel']} – *{buch['autor']}*", inline=False)
        embed.add_field(name="📅 Zeitraum", value=f"{buch['start_datum'].strftime('%d.%m.%Y')} – {buch['end_datum'].strftime('%d.%m.%Y')}", inline=True)
        embed.add_field(name="⭐ Durchschnitt", value=sterne_anzeige(float(avg)), inline=True)
        embed.add_field(name="🗳️ Bewertungen", value=str(count), inline=True)

        await kanal.send(embed=embed)

        # Aktive Bewertung deaktivieren
        if buch['id'] in self.aktive_bewertungen:
            msg, view, _ = self.aktive_bewertungen.pop(buch['id'])
            for item in view.children:
                item.disabled = True
            try:
                await msg.edit(view=view)
            except Exception:
                pass

    @check_bewertungen.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(Bewertung(bot))
