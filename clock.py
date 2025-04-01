#!/usr/bin/python3

import asyncio
import datetime
import logging
import math
import sys
import traceback

import phatbeat
import scrollphathd as sphd
from aiohttp import web
from scrollphathd.fonts import font3x5, font5x7

logging.basicConfig(
    level=logging.DEBUG,
    filename="/tmp/clock.log",
    filemode="w+",
    format="%(asctime)s - %(message)s",
)

action_lock = asyncio.Lock()


def my_handler(exc_type, exc_value, exc_tb):
    exception_text = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    logging.exception("Uncaught exception: %s", exception_text)


sys.excepthook = my_handler


async def handle_post(request):
    data = await request.text()
    data = data[:100]
    logging.debug("Received: %s", data)
    await action_lock.acquire()
    sphd.write_string(data, brightness=1.0, font=font5x7)
    (w, h) = sphd.get_buffer_shape()
    logging.debug("Buffer size %sx%s", w, h)
    for _ in range(w * 2):
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


def emit_sound(now):
    if now.hour in [0, 1, 2, 3, 4, 5, 6]:
        return False
    return True


def log_time(now):
    time_string = (
        f"{now.year}-{now.month:02d}-{now.day:02d}({now.weekday()}) - "
        f"{now.hour:02d}:{now.minute:02d}:{now.second:02d}"
    )
    if now.second in [0, 1]:
        logging.debug(time_string)


def set_day_of_week(now):
    # clean all day of week VU Leds
    phatbeat.clear(channel=0)
    # We start from the left
    day_led = 7 - now.weekday()
    phatbeat.set_pixel(day_led, 0, 0, 254, brightness=1.0, channel=0)
    phatbeat.show()


def set_hour_leds(now):
    minute_led = 7 - math.floor(now.minute / 10)
    for x in range(minute_led, 7 + 1):
        phatbeat.set_pixel(x, 0, 254, 0, brightness=0.05, channel=1)
    phatbeat.show()


# Displays the time on the clock and the day of the weak on the
async def background_tasks():
    last_hour = None
    last_minute = None
    hour_counter = 0
    while True:
        now = get_time()
        log_time(now)
        current_hour = now.hour
        current_minute = now.minute
        if current_hour != last_hour:
            set_day_of_week(now)
            phatbeat.clear(channel=1)  # Every hour clean the hour progress bar
            phatbeat.show()
            last_hour = current_hour
            hour_counter += 1

        if current_minute != last_minute:
            set_hour_leds(now)
            last_minute = current_minute

        b = brightness(now.hour, now.minute, now.second)
        if action_lock.locked():
            logging.debug("Lock is taken, skipping clock update")
        else:
            st = f"{now.hour:02d}:{now.minute:02d}"
            show_time(st, bright=b)

        await asyncio.sleep(1)


async def main():
    logging.info("Setting up sound...")
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
