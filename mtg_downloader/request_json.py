import sys, os, re, requests, cloudscraper, subprocess, time, threading, asyncio
from functools import partial
import aiometer, httpx


MAX_REQUESTS_PER_SEC = 3
session = httpx.AsyncClient()

async def __scrape(url, result):
    try:
        response = await session.get(url)
        result.append(response.json())
        print(f"Scrappeo completado de {url}")
        return response.json()
    except Exception as e:
        print(e)
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

#semaphore = threading.Semaphore(MAX_REQUESTS_PER_SEC)
#
#def __refill_semaphone():
#    while True:
#        time.sleep(1 / MAX_REQUESTS_PER_SEC + 0.2)
#        try:
#            semaphore.release()
#        except:
#            # Ya estaba lleno, no hace nada
#            pass
#threading.Thread(target=__refill_semaphone, daemon=True).start()
#
#def start_semaphore(max_req_per_sec:int):
#    global MAX_REQUESTS_PER_SEC, semaphore
#    if max_req_per_sec <= 0:
#        print(f"Las requests por segundo ({max_req_per_sec}) deben ser mayor que 0")
#        return
#    
#    MAX_REQUESTS_PER_SEC = max_req_per_sec
#    semaphore = threading.Semaphore(MAX_REQUESTS_PER_SEC)
#    __refill_semaphone()
#