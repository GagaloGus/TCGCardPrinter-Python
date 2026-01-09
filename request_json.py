import sys, os, time, asyncio
from functools import partial
import aiometer, httpx

session = httpx.AsyncClient()

async def __scrape(url, result):
    try:
        response = await session.get(url)
        res = (url, response.json())
        print(f"Scrappeo completado de {res[0]}")
        result.append(res)
        return res
    except Exception as e:
        print(f"\033[31mError de scrappeo: \033[0m {e}")
        return None
        

async def __scrape_json(urls : list[str], max_per_sec, result):
    _start = time.time()
    
    scrape_with_result = partial(__scrape, result=result)
    
    await aiometer.run_on_each(
        scrape_with_result, 
        urls,
        max_per_second=max_per_sec,  # here we can set max rate per second
    )
    print(f"finished {len(urls)} requests in {time.time() - _start:.2f} seconds")

def run(urls : list[str], result, max_per_sec = 2.5):
    asyncio.run(__scrape_json(urls, max_per_sec, result))

if __name__ == "__main__":
    urls = ["https://api.scryfall.com/cards/multiverse/1508" for _ in range(10)]
    res = []
    run(urls, res)
    print(res)