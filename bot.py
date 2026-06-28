import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import database as db
from aiohttp import web

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ── UptimeRobot Webserver (Render braucht einen offenen Port) ──────────────
async def health(request):
    return web.Response(text="OK")

async def start_webserver():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 8080)))
    await site.start()

# ──────────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ Bot eingeloggt als {bot.user}")
    await db.init_db()
    await bot.load_extension("cogs.panel")
    await bot.load_extension("cogs.bewertung")
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} Slash-Commands synchronisiert")
    except Exception as e:
        print(f"❌ Fehler beim Sync: {e}")

async def main():
    await start_webserver()
    await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())
