import asyncpg
import os

pool = None

async def init_db():
    global pool
    pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"), ssl="require")
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS buecher (
                id SERIAL PRIMARY KEY,
                titel TEXT NOT NULL,
                autor TEXT NOT NULL,
                genre TEXT NOT NULL,
                seiten INTEGER NOT NULL,
                start_datum DATE NOT NULL,
                end_datum DATE NOT NULL,
                bewertung_offen BOOLEAN DEFAULT TRUE,
                bewertung_nachricht_id BIGINT,
                bewertung_kanal_id BIGINT,
                erstellt_am TIMESTAMPTZ DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS bewertungen (
                id SERIAL PRIMARY KEY,
                buch_id INTEGER REFERENCES buecher(id),
                user_id BIGINT NOT NULL,
                sterne NUMERIC(2,1) NOT NULL,
                erstellt_am TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(buch_id, user_id)
            );
        """)

async def buch_eintragen(titel, autor, genre, seiten, start_datum, end_datum):
    async with pool.acquire() as conn:
        return await conn.fetchrow(
            """INSERT INTO buecher (titel, autor, genre, seiten, start_datum, end_datum)
               VALUES ($1, $2, $3, $4, $5, $6) RETURNING id""",
            titel, autor, genre, seiten, start_datum, end_datum
        )

async def alle_buecher():
    async with pool.acquire() as conn:
        return await conn.fetch(
            """SELECT b.*, 
                      COALESCE(AVG(bw.sterne), 0) as avg_bewertung,
                      COUNT(bw.id) as anzahl_bewertungen
               FROM buecher b
               LEFT JOIN bewertungen bw ON b.id = bw.buch_id
               GROUP BY b.id
               ORDER BY b.start_datum ASC"""
        )

async def statistiken():
    async with pool.acquire() as conn:
        buecher_anzahl = await conn.fetchval("SELECT COUNT(*) FROM buecher")
        gesamtseiten = await conn.fetchval("SELECT COALESCE(SUM(seiten), 0) FROM buecher")
        genres = await conn.fetch(
            "SELECT genre, COUNT(*) as anzahl FROM buecher GROUP BY genre ORDER BY anzahl DESC"
        )
        return buecher_anzahl, gesamtseiten, genres

async def bewertung_speichern(buch_id, user_id, sterne):
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                """INSERT INTO bewertungen (buch_id, user_id, sterne)
                   VALUES ($1, $2, $3)
                   ON CONFLICT (buch_id, user_id) DO UPDATE SET sterne = $3""",
                buch_id, user_id, sterne
            )
            return True
        except Exception:
            return False

async def buecher_fuer_bewertung_heute(heute):
    async with pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM buecher WHERE end_datum = $1 AND bewertung_offen = TRUE",
            heute
        )

async def bewertung_schliessen_vorbereiten(buch_id, nachricht_id, kanal_id):
    async with pool.acquire() as conn:
        await conn.execute(
            """UPDATE buecher SET bewertung_nachricht_id = $2, bewertung_kanal_id = $3
               WHERE id = $1""",
            buch_id, nachricht_id, kanal_id
        )

async def bewertung_schliessen(buch_id, nachricht_id, kanal_id):
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE buecher SET bewertung_offen = FALSE WHERE id = $1",
            buch_id
        )

async def buch_bewertungen(buch_id):
    async with pool.acquire() as conn:
        avg = await conn.fetchval(
            "SELECT COALESCE(AVG(sterne), 0) FROM bewertungen WHERE buch_id = $1", buch_id
        )
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM bewertungen WHERE buch_id = $1", buch_id
        )
        return avg, count

async def buch_by_id(buch_id):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT * FROM buecher WHERE id = $1", buch_id)
