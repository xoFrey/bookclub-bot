import discord
from discord.ext import commands
import asyncio
import database as db

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


async def delete_after(msg, delay=86400):
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass


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
        await db.bewertung_speichern(self.buch_id, interaction.user.id, sterne)
        await interaction.response.send_message(
            f"✅ **{interaction.user.display_name}** hat **{sterne} ⭐** gegeben!"
        )
        msg = await interaction.original_response()
        asyncio.create_task(delete_after(msg, 86400))


class BewertungAbschliessenButton(discord.ui.Button):
    def __init__(self, buch_id: int):
        self.buch_id = buch_id
        super().__init__(label="✅ Bewertung abschließen", style=discord.ButtonStyle.success, custom_id=f"abschliessen_{buch_id}")

    async def callback(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Nur Admins.", ephemeral=True)
            return

        buch = await db.buch_by_id(self.buch_id)
        avg, count = await db.buch_bewertungen(self.buch_id)
        await db.bewertung_schliessen(self.buch_id, None, None)

        # Bewertungsfenster löschen
        await interaction.message.delete()

        embed = discord.Embed(
            title="📊 Bewertungsergebnis",
            description=f"Die Bewertungsphase für **{buch['titel']}** ist abgeschlossen!",
            color=discord.Color.green()
        )
        embed.add_field(name="📖 Buch", value=f"{buch['titel']} – *{buch['autor']}*", inline=False)
        embed.add_field(name="📅 Zeitraum", value=f"{buch['start_datum'].strftime('%d.%m.%Y')} – {buch['end_datum'].strftime('%d.%m.%Y')}", inline=True)
        embed.add_field(name="⭐ Durchschnitt", value=sterne_anzeige(float(avg)), inline=True)
        embed.add_field(name="🗳️ Bewertungen", value=str(count), inline=True)
        await interaction.response.send_message(embed=embed)


class BewertungView(discord.ui.View):
    def __init__(self, buch_id: int):
        super().__init__(timeout=None)
        self.add_item(BewertungSelect(buch_id))
        self.add_item(BewertungAbschliessenButton(buch_id))


class Bewertung(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def bewertung_starten(self, buch, kanal):
        embed = discord.Embed(
            title="📚 Buchbewertung!",
            description=f"**{buch['titel']}** von *{buch['autor']}* ist fertig!\n\nGibt eure Bewertung ab! ⭐",
            color=discord.Color.orange()
        )
        embed.add_field(name="📅 Zeitraum", value=f"{buch['start_datum'].strftime('%d.%m.%Y')} – {buch['end_datum'].strftime('%d.%m.%Y')}", inline=True)
        embed.add_field(name="🏷️ Genre", value=buch['genre'], inline=True)
        embed.add_field(name="", value="*Admin kann die Bewertung jederzeit manuell abschließen.*", inline=False)

        view = BewertungView(buch['id'])
        await kanal.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(Bewertung(bot))
