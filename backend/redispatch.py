import sys
import asyncio
import os

sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv('.env')

from tasks.processing_pipeline import process_document
import asyncpg

url = os.getenv('DATABASE_URL').replace('postgresql+asyncpg://', 'postgresql://')

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def go():
    conn = await asyncpg.connect(url, statement_cache_size=0)
    jobs = await conn.fetch("SELECT id FROM jobs WHERE status='queued'")
    for j in jobs:
        process_document.delay(str(j['id']))
        print('dispatched', j['id'])
    print(f'Total: {len(jobs)} job(s) dispatched')
    await conn.close()

asyncio.run(go())
