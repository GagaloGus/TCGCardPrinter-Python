import sys, os, re, requests, cloudscraper, subprocess, time, threading, asyncio

import aiometer, httpx

MAX_REQUESTS_PER_SEC = 3

session = httpx.AsyncClient()

async def scrape(url):
    response = await session.get(url)
    return response

async def run():
    _start = time.time()
    urls = ["https://api.scryfall.com/cards/multiverse/1508" for i in range(10)]
    results = await aiometer.run_on_each(
        scrape, 
        urls,
        max_per_second=2.5,  # here we can set max rate per second
    )
    print(f"finished {len(urls)} requests in {time.time() - _start:.2f} seconds")
    return results

if __name__ == "__main__":
    asyncio.run(run())

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
