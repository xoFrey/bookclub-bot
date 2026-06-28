import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import traceback
import database as db
from aiohttp import web

load_dotenv()

KANAL_ID = 1520833897917583542

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

async def health(request):
    return web.Response(text="OK")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    await site.start()
    print("✅ Webserver gestartet")

@bot.event
async def on_ready():
    print(f"✅ Bot eingeloggt als {bot.user}")
    try:
        await db.init_db()
        print("✅ Datenbank verbunden")
    except Exception as e:
        print(f"❌ DB Fehler: {e}")
        traceback.print_exc()
        return

    kanal = bot.get_channel(KANAL_ID)
    if not kanal:
        print(f"❌ Kanal {KANAL_ID} nicht gefunden")
        return

    from panel import PanelView
    embed = discord.Embed(
        title="📚 Buchclub Panel",
        description="Willkommen im Buchclub! Wähle eine Aktion:",
        color=discord.Color.purple()
    )
    await kanal.send(embed=embed, view=PanelView())
    print("✅ Panel gepostet")

async def main():
    print("🔄 Starte...")
    await start_webserver()
    await bot.load_extension("panel")
    await bot.load_extension("bewertung")
    await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())
