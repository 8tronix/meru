import asyncio
import logging
import os
import signal
import traceback
from importlib import import_module
from typing import Callable

from meru.exceptions import PingTimeout
from meru.log import setup_logging
from meru.sockets import MessagingSocket

logger = logging.getLogger("meru.core")


async def shutdown(loop, process_signal=None):
    """Cleanup tasks tied to the service's shutdown."""
    if process_signal:
        logger.info(f"Received exit signal {process_signal.name}...")
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]

    logger.info(f"Cancelling {len(tasks)} outstanding tasks")
    for task in tasks:
        task.cancel()

    await asyncio.gather(*tasks, return_exceptions=True)

    # https://github.com/zeromq/pyzmq/issues/1167
    logger.debug("Destroying ZMQ context.")
    MessagingSocket.ctx.destroy(linger=0)

    loop.stop()


def handle_exception(loop, context):
    exception = context.get("exception", context["message"])

    if isinstance(exception, PingTimeout):
        logger.error("Ping timeout with broker... shutting down")
    else:
        logger.error(f"Caught exception: {exception}")
        # Note: Find a way to properly log the traceback
        traceback.print_tb(exception.__traceback__)
        logger.info("Shutting down...")

    asyncio.create_task(shutdown(loop))


def import_runner(full_path) -> Callable:
    mod_path = ".".join(full_path.split(".")[:-1])
    func = full_path.split(".")[-1]

    mod = import_module(mod_path)
    return getattr(mod, func)


def run_process(entry_point_path):
    """Start a process.

    Parameters:
        entry_point_path: Python module path to the entrypoint.  E.g. `"my_app.processes.a_process.func"`.
    """
    setup_logging()
    entry_point = import_runner(entry_point_path)
    os.environ["MERU_PROCESS"] = entry_point.__name__
    loop = asyncio.get_event_loop()

    signals = (signal.SIGHUP, signal.SIGTERM, signal.SIGINT)
    for sig in signals:
        loop.add_signal_handler(
            sig, lambda s=sig: asyncio.create_task(shutdown(loop, process_signal=s))
        )

    loop.set_exception_handler(handle_exception)
    loop.create_task(entry_point())

    logger.info(f"Process ID: {os.getpid()}")

    loop.run_forever()
