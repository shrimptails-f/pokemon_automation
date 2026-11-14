import asyncio
import threading
import unittest

from automation.adapters.discord.review import DiscordPorts


class DiscordCancellationTests(unittest.IsolatedAsyncioTestCase):
    async def test_stop_interrupts_pending_review(self):
        stop = threading.Event()
        ports = DiscordPorts(asyncio.get_running_loop(), None, None, None, 1, stop)
        started = asyncio.Event()

        async def wait_forever():
            started.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(asyncio.to_thread(ports.call, wait_forever()))
        await asyncio.wait_for(started.wait(), 1)
        stop.set()
        with self.assertRaises(InterruptedError):
            await asyncio.wait_for(task, 2)


if __name__ == '__main__':
    unittest.main()
