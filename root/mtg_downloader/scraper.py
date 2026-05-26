import asyncio
import httpx
import time
from functools import partial
import aiometer


async def _scrape(session, url, result):
    try:
        response = await session.get(url)
        json = response.json()
        result.append((url, json))
        print(f"Scrappeo completado de {url}")
    except Exception as e:
        print(f"\033[31mError de scrappeo:\033[0m {e}")


async def scrape_json(urls : list, result, max_per_sec : int):
    start = time.time()

    async with httpx.AsyncClient() as session:
        scrape = partial(_scrape, session, result=result)

        await aiometer.run_on_each(
            scrape,
            urls,
            max_per_second=max_per_sec,
        )

    print(f"finished {len(urls)} requests in {time.time() - start:.2f} seconds")