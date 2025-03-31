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


def my_handler(mytype, value, tb):
    logging.exception(f"Uncaught exception: {value}")


sys.excepthook = my_handler


async def handle_post(request):
    data = await request.text()
    logging.debug(f"Received: {data}")
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
    time_string = "%s-%s-%s(%s) - %s:%s:%s" % (
        now.year,
        now.month,
        now.day,
        now.weekday(),
        now.hour,
        now.minute,
        now.second,
    )
    if now.second in [0, 1]:
        logging.debug(time_string)


async def background_tasks():
    while True:
        now = get_time()
        log_time(now)
        b = brightness(now.hour, now.minute, now.second)
        st = "%02d:%02d " % (now.hour, now.minute)
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
