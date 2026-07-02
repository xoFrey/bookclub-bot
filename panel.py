import discord
from discord.ext import commands
import database as db
from datetime import date

GENRES = [
    "Fantasy", "Science Fiction", "Krimi", "Thriller", "Roman",
    "Historisch", "Horror", "Romantik", "Sachbuch", "Biografie",
    "Jugend", "Klassiker", "Abenteuer", "Mystery", "Sonstiges"
]

def sterne_anzeige(avg):
    voll = int(avg)
    halb = 1 if (avg - voll) >= 0.5 else 0
    return "⭐" * voll + ("✨" if halb else "") + f" ({avg:.1f})"


class BuchEintragenModal(discord.ui.Modal, title="📚 Buch eintragen"):
    buch_titel = discord.ui.TextInput(label="Titel", placeholder="z.B. Der Herr der Ringe")
    autor = discord.ui.TextInput(label="Autor", placeholder="z.B. J.R.R. Tolkien")
    seiten = discord.ui.TextInput(label="Seitenzahl", placeholder="z.B. 423")
    start_datum = discord.ui.TextInput(label="Startdatum", placeholder="TT.MM.JJJJ")
    end_datum = discord.ui.TextInput(label="Enddatum", placeholder="TT.MM.JJJJ")

    def __init__(self, genre: str):
        super().__init__()
        self.genre = genre

    async def on_submit(self, interaction: discord.Interaction):
        try:
            seiten_int = int(self.seiten.value.strip())
            start = date(*reversed([int(x) for x in self.start_datum.value.strip().split(".")]))
            end = date(*reversed([int(x) for x in self.end_datum.value.strip().split(".")]))
        except Exception:
            await interaction.response.send_message(
                "❌ Ungültige Eingabe. Bitte Datum im Format TT.MM.JJJJ und Seitenzahl als Zahl eingeben.",
                ephemeral=True
            )
            return

        if end <= start:
            await interaction.response.send_message("❌ Enddatum muss nach dem Startdatum liegen.", ephemeral=True)
            return

        await db.buch_eintragen(
            self.buch_titel.value.strip(),
            self.autor.value.strip(),
            self.genre,
            seiten_int,
            start,
            end
        )

        embed = discord.Embed(title="✅ Buch eingetragen!", color=discord.Color.green())
        embed.add_field(name="📖 Titel", value=self.buch_titel.value.strip(), inline=True)
        embed.add_field(name="✍️ Autor", value=self.autor.value.strip(), inline=True)
        embed.add_field(name="🏷️ Genre", value=self.genre, inline=True)
        embed.add_field(name="📄 Seiten", value=str(seiten_int), inline=True)
        embed.add_field(name="📅 Zeitraum", value=f"{self.start_datum.value} – {self.end_datum.value}", inline=True)
        await interaction.response.send_message(embed=embed)


class GenreSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=g, value=g) for g in GENRES]
        super().__init__(placeholder="Genre auswählen...", options=options, min_values=1, max_values=1)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(BuchEintragenModal(genre=self.values[0]))


class GenreView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.add_item(GenreSelect())


class BuchBeendenSelect(discord.ui.Select):
    def __init__(self, buecher):
        options = [
            discord.SelectOption(
                label=f"{b['titel']} – {b['autor']}",
                value=str(b['id']),
                description=f"Endet: {b['end_datum'].strftime('%d.%m.%Y')}"
            ) for b in buecher
        ]
        super().__init__(placeholder="Buch auswählen...", options=options)

    async def callback(self, interaction: discord.Interaction):
        buch_id = int(self.values[0])
        buch = await db.buch_by_id(buch_id)
        await interaction.response.send_message(f"✅ Bewertungsphase für **{buch['titel']}** gestartet!", ephemeral=False)
        cog = interaction.client.cogs.get("Bewertung")
        if cog:
            await cog.bewertung_starten(buch, interaction.channel)


class BuchBeendenView(discord.ui.View):
    def __init__(self, buecher):
        super().__init__(timeout=60)
        self.add_item(BuchBeendenSelect(buecher))


class PanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📚 Buch Eintragen", style=discord.ButtonStyle.primary, custom_id="buch_eintragen")
    async def buch_eintragen(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Nur Admins können Bücher eintragen.", ephemeral=True)
            return
        view = GenreView()
        await interaction.response.send_message("Bitte zuerst das Genre auswählen:", view=view, ephemeral=True)

    @discord.ui.button(label="📊 Statistiken", style=discord.ButtonStyle.secondary, custom_id="statistiken")
    async def statistiken(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_admin = interaction.user.guild_permissions.administrator
        anzahl, seiten, genres = await db.statistiken()
        embed = discord.Embed(title="📊 Buchclub Statistiken", color=discord.Color.blue())
        embed.add_field(name="📚 Bücher gesamt", value=str(anzahl), inline=True)
        embed.add_field(name="📄 Gesamtseiten", value=str(seiten), inline=True)
        if genres:
            genre_text = "\n".join([f"**{g['genre']}** – {g['anzahl']}x" for g in genres])
            embed.add_field(name="🏷️ Genres", value=genre_text, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=not is_admin)

    @discord.ui.button(label="📖 Bücherliste", style=discord.ButtonStyle.secondary, custom_id="buecherliste")
    async def buecherliste(self, interaction: discord.Interaction, button: discord.ui.Button):
        is_admin = interaction.user.guild_permissions.administrator
        buecher = await db.alle_buecher()
        if not buecher:
            await interaction.response.send_message("📭 Noch keine Bücher eingetragen.", ephemeral=True)
            return
        embed = discord.Embed(title="📖 Bücherliste", color=discord.Color.gold())
        for b in buecher:
            avg = float(b['avg_bewertung'])
            bewertung_str = sterne_anzeige(avg) if b['anzahl_bewertungen'] > 0 else "Noch keine Bewertung"
            embed.add_field(
                name=f"📘 {b['titel']} – {b['autor']}",
                value=(
                    f"🏷️ {b['genre']} | 📄 {b['seiten']} Seiten\n"
                    f"📅 {b['start_datum'].strftime('%d.%m.%Y')} – {b['end_datum'].strftime('%d.%m.%Y')}\n"
                    f"⭐ {bewertung_str} ({b['anzahl_bewertungen']} Bewertungen)"
                ),
                inline=False
            )
        await interaction.response.send_message(embed=embed, ephemeral=not is_admin)

    @discord.ui.button(label="🔚 Buch beenden", style=discord.ButtonStyle.danger, custom_id="buch_beenden")
    async def buch_beenden(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Nur Admins.", ephemeral=True)
            return
        buecher = await db.offene_buecher()
        if not buecher:
            await interaction.response.send_message("📭 Keine aktiven Bücher.", ephemeral=True)
            return
        view = BuchBeendenView(buecher)
        await interaction.response.send_message("Welches Buch soll beendet werden?", view=view, ephemeral=True)


class Panel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(Panel(bot))


class PublicView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📊 Statistiken", style=discord.ButtonStyle.secondary, custom_id="pub_statistiken")
    async def statistiken(self, interaction: discord.Interaction, button: discord.ui.Button):
        anzahl, seiten, genres = await db.statistiken()
        embed = discord.Embed(title="📊 Buchclub Statistiken", color=discord.Color.blue())
        embed.add_field(name="📚 Bücher gesamt", value=str(anzahl), inline=True)
        embed.add_field(name="📄 Gesamtseiten", value=str(seiten), inline=True)
        if genres:
            genre_text = "\n".join([f"**{g['genre']}** – {g['anzahl']}x" for g in genres])
            embed.add_field(name="🏷️ Genres", value=genre_text, inline=False)
        await interaction.response.send_message(embed=embed)

    @discord.ui.button(label="📖 Bücherliste", style=discord.ButtonStyle.secondary, custom_id="pub_buecherliste")
    async def buecherliste(self, interaction: discord.Interaction, button: discord.ui.Button):
        buecher = await db.alle_buecher()
        if not buecher:
            await interaction.response.send_message("📭 Noch keine Bücher eingetragen.", ephemeral=True)
            return
        embed = discord.Embed(title="📖 Bücherliste", color=discord.Color.gold())
        for b in buecher:
            avg = float(b['avg_bewertung'])
            bewertung_str = sterne_anzeige(avg) if b['anzahl_bewertungen'] > 0 else "Noch keine Bewertung"
            embed.add_field(
                name=f"📘 {b['titel']} – {b['autor']}",
                value=(
                    f"🏷️ {b['genre']} | 📄 {b['seiten']} Seiten\n"
                    f"📅 {b['start_datum'].strftime('%d.%m.%Y')} – {b['end_datum'].strftime('%d.%m.%Y')}\n"
                    f"⭐ {bewertung_str} ({b['anzahl_bewertungen']} Bewertungen)"
                ),
                inline=False
            )
        await interaction.response.send_message(embed=embed)
