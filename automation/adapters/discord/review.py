"""Discord implementation of the synchronous review and status ports."""
import asyncio
from concurrent.futures import TimeoutError as FutureTimeout
from datetime import datetime, timezone
import os
from pathlib import Path

import discord
from dotenv import load_dotenv

class ReviewView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.choice = False
        self.lock = asyncio.Lock()

    async def interaction_check(self, interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("この操作は許可されていません。", ephemeral=True)
            return False
        return True

    async def choose(self, interaction, choice):
        async with self.lock:
            if self.is_finished():
                await interaction.response.send_message("この確認は終了しています。", ephemeral=True)
                return
            for item in self.children:
                item.disabled = True
            await interaction.response.edit_message(content=f"確認結果: {'再開' if choice else '停止'}", view=self)
            self.choice = choice
            self.stop()

    @discord.ui.button(label="通常色・リセットして再開", style=discord.ButtonStyle.primary)
    async def resume(self, interaction, button):
        await self.choose(interaction, True)

    @discord.ui.button(label="停止", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction, button):
        await self.choose(interaction, False)


class DiscordPorts:
    def __init__(self, loop, client, thread, message, user_id, stop):
        self.loop, self.client, self.thread, self.message, self.user_id = loop, client, thread, message, user_id
        self.stop = stop
        self.attempt = 0

    def call(self, coroutine):
        future = asyncio.run_coroutine_threadsafe(coroutine, self.loop)
        while True:
            try:
                return future.result(timeout=0.2)
            except FutureTimeout:
                if self.stop.is_set():
                    future.cancel()
                    raise InterruptedError("中止しました。")

    def update(self, attempt, state):
        self.attempt = attempt
        async def update_message():
            if not self.client.is_ready():
                raise RuntimeError("Discord が切断されたため停止します。")
            timestamp = int(datetime.now(timezone.utc).timestamp())
            await self.message.edit(content=f"**BDSP 周回状況**\n状態: {state}\n現在: {attempt}回目\n最終更新: <t:{timestamp}:F>")
        self.call(update_message())

    def should_reset(self, result):
        async def ask():
            images = sorted(result.directory.glob("frame_*.png"))
            if not images or len(images) > 10:
                raise RuntimeError("確認画像を送信できません。")
            view = ReviewView(self.user_id)
            files = [discord.File(str(path)) for path in images]
            try:
                await self.thread.send(f"<@{self.user_id}> {self.attempt}回目: {result.classification}。画像を確認してください。",
                                       files=files, view=view,
                                       allowed_mentions=discord.AllowedMentions(users=True, roles=False, everyone=False))
            finally:
                for file in files:
                    file.close()
            await view.wait()
            return view.choice
        self.update(self.attempt, "画像確認待ち")
        return self.call(ask())


async def run(args, token, channel_id, user_id, encounter, reset, run_loop, stop):
    client = discord.Client(intents=discord.Intents.none())
    started = False
    failure = None
    worker = None

    @client.event
    async def on_ready():
        nonlocal started, failure, worker
        if started:
            return
        started = True
        try:
            channel = await client.fetch_channel(channel_id)
            thread = await channel.create_thread(name="BDSP 周回状況", type=discord.ChannelType.public_thread)
            print(f"スレッド: {thread.jump_url}", flush=True)
            message = await thread.send("BDSP 周回を開始します。")
            ports = DiscordPorts(asyncio.get_running_loop(), client, thread, message, user_id, stop)
            worker = asyncio.create_task(asyncio.to_thread(run_loop, encounter, reset, ports, ports,
                                         auto_reset=args.auto_reset, reset_first=args.reset_first))
            await asyncio.shield(worker)
        except Exception as exc:
            failure = exc
            if 'ports' in locals() and client.is_ready():
                try:
                    await message.edit(content=f"**BDSP 周回状況**\n状態: エラーで停止。PCを確認してください\n現在: {ports.attempt}回目\n最終更新: <t:{int(datetime.now(timezone.utc).timestamp())}:F>")
                except discord.DiscordException:
                    pass
        finally:
            stop.set()
            if worker and not worker.done():
                try:
                    await asyncio.shield(worker)
                except Exception:
                    pass
            await client.close()

    try:
        await client.start(token)
    finally:
        stop.set()
    if failure:
        raise RuntimeError(f"Discord 周回に失敗しました: {failure}") from failure


def main(args, encounter, reset, run_loop, stop, legacy_env=None):
    root = Path(__file__).resolve().parents[3]
    load_dotenv(root / ".env", override=False)
    if legacy_env:
        load_dotenv(legacy_env, override=False)
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    channel = os.environ.get("DISCORD_CHANNEL_ID", "").strip()
    user = os.environ.get("DISCORD_USER_ID", "").strip()
    if not token or not channel.isascii() or not channel.isdigit() or not user.isascii() or not user.isdigit():
        raise RuntimeError(".env に DISCORD_BOT_TOKEN、DISCORD_CHANNEL_ID、DISCORD_USER_ID を設定してください。")
    asyncio.run(run(args, token, int(channel), int(user), encounter, reset, run_loop, stop))
