import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import traceback
from aiohttp import web

load_dotenv()

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
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} Slash-Commands synchronisiert")
    except Exception as e:
        print(f"❌ Sync Fehler: {e}")
        traceback.print_exc()

async def main():
    print("🔄 Starte Webserver...")
    await start_webserver()
    print("🔄 Lade Extensions...")
    await bot.load_extension("panel")
    await bot.load_extension("bewertung")
    print("✅ Extensions geladen")
    print("🔄 Starte Bot...")
    await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())
