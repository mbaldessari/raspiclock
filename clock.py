#!/usr/bin/python3

import asyncio
import datetime
import logging
import sys

import phatbeat
import scrollphathd as sphd
from aiohttp import web
from scrollphathd.fonts import font3x5

logging.basicConfig(
    level=logging.DEBUG,
    filename="/tmp/clock.log",
    filemode="w+",
    format="%(asctime)s - %(message)s",
)

action_lock = asyncio.Lock()


def my_handler(_mytype, value, _tb):
    logging.exception("Uncaught exception: %s", value)


sys.excepthook = my_handler


async def handle_post(request):
    data = await request.text()
    logging.debug("Received: %s", data)
    await action_lock.acquire()
    sphd.write_string(data, brightness=1.0, font=font3x5)
    for i in range(100):
        sphd.show()
        sphd.scroll(1)
        await asyncio.sleep(0.05)
    await asyncio.sleep(2)
    action_lock.release()

    return web.Response(text="OK")


def get_time():
    return datetime.datetime.now()


def show_time(s, bright=0.1):
    sphd.clear()
    sphd.write_string(s, brightness=bright, font=font3x5)
    sphd.show()


# Turn off from 23:01 to 5:59
# low brightness normally
# high brightness for 6 seconds at the start of the hour
def brightness(h, m, s):
    if h in [0, 1, 2, 3, 4, 5, 6]:
        return 0.0
    if m in [0] and s in [0, 1, 2, 3, 4, 5]:
        return 1.0
    return 0.1


def log_time(now):
    time_string = (
        f"{now.year}-{now.month:02d}-{now.day:02d}({now.weekday()}) - "
        f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}"
    )
    if now.second in [0, 1]:
        logging.debug(time_string)


async def background_tasks():
    while True:
        now = get_time()
        log_time(now)
        b = brightness(now.hour, now.minute, now.second)
        st = f"{now.hour:02d}:{now.minute:02d}"
        if action_lock.locked():
            logging.debug("Lock is taken, skipping clock update")
        else:
            show_time(st, bright=b)
        await asyncio.sleep(1)


async def main():
    for channel in (0, 1):
        phatbeat.set_pixel(0, 255, 255, 0, channel=channel)
    phatbeat.show()
    logging.info("Setting up webport...")
    app = web.Application()
    app.router.add_post("/receive", handle_post)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, port=8080)
    await site.start()
    logging.info("Starting clock service...")
    sphd.flip(x=True, y=True)
    await asyncio.gather(
        background_tasks(),
        asyncio.Event().wait(),
    )


if __name__ == "__main__":
    asyncio.run(main())
