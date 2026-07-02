import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
import asyncio
import traceback
import database as db
from aiohttp import web

load_dotenv()

KANAL_ADMIN = 1522224891070251048
KANAL_PUBLIC = 1522225490197348402

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

    from panel import PanelView, PublicView

    # # Kanal 1 – alle Buttons
    # kanal_admin = bot.get_channel(KANAL_ADMIN)
    # if kanal_admin:
    #     embed = discord.Embed(
    #         title="📚 Buchclub Panel",
    #         description="Willkommen im Buchclub! Wähle eine Aktion:",
    #         color=discord.Color.purple()
    #     )
    #     await kanal_admin.send(embed=embed, view=PanelView())
    #     print("✅ Admin-Panel gepostet")
    # else:
    #     print(f"❌ Admin-Kanal {KANAL_ADMIN} nicht gefunden")

    # # Kanal 2 – nur Statistiken & Bücherliste
    # kanal_public = bot.get_channel(KANAL_PUBLIC)
    # if kanal_public:
    #     embed = discord.Embed(
    #         title="📚 Buchclub",
    #         description="Hier könnt ihr die Bücherliste und Statistiken einsehen:",
    #         color=discord.Color.blurple()
    #     )
    #     await kanal_public.send(embed=embed, view=PublicView())
    #     print("✅ Public-Panel gepostet")
    # else:
    #     print(f"❌ Public-Kanal {KANAL_PUBLIC} nicht gefunden")

async def main():
    print("🔄 Starte...")
    await start_webserver()
    await bot.load_extension("panel")
    await bot.load_extension("bewertung")
    await bot.start(os.getenv("DISCORD_TOKEN"))

asyncio.run(main())
