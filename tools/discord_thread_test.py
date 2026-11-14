"""Test a Discord status thread independently of Switch operations."""
import argparse
import asyncio
from datetime import datetime, timezone
import os
import sys

try:
    import discord
except ImportError:
    sys.exit("discord.py が必要です: python -m pip install discord.py")


def status(state, count):
    timestamp = int(datetime.now(timezone.utc).timestamp())
    return f"**BDSP 周回状況（テスト）**\n状態: {state}\n現在: {count}回目\n最終更新: <t:{timestamp}:F>"


async def run(token, channel_id, count, interval):
    client = discord.Client(intents=discord.Intents.none())
    started = False
    failure = None

    @client.event
    async def on_ready():
        nonlocal started, failure
        if started:
            return
        started = True
        try:
            channel = await client.fetch_channel(channel_id)
            thread = await channel.create_thread(name="BDSP 周回状況テスト", type=discord.ChannelType.public_thread)
            print(f"スレッドを作成しました: {thread.jump_url}", flush=True)
            message = await thread.send(status("テスト開始", 0))
            for attempt in range(1, count + 1):
                await asyncio.sleep(interval)
                await message.edit(content=status("自動周回中（テスト）", attempt))
                print(f"{attempt}回目に更新しました。", flush=True)
            await message.edit(content=status("テスト終了", count))
            print("テスト終了。Discord のスレッドを確認してください。", flush=True)
        except (discord.DiscordException, OSError) as exc:
            failure = exc
        finally:
            await client.close()

    await client.start(token)
    if failure:
        raise failure


def main():
    parser = argparse.ArgumentParser(description="Discord のスレッドと状況更新を単独テスト")
    parser.add_argument("channel_id", type=int, help="スレッドを作成するテキストチャンネル ID")
    parser.add_argument("--count", type=int, default=3, help="更新回数（既定: 3）")
    parser.add_argument("--interval", type=float, default=10, help="更新間隔の秒数（既定: 10）")
    args = parser.parse_args()
    if not 1 <= args.count <= 100 or not 5 <= args.interval <= 3600:
        parser.error("count は 1〜100、interval は 5〜3600 にしてください")
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        sys.exit("環境変数 DISCORD_BOT_TOKEN に Bot トークンを設定してください。")
    try:
        asyncio.run(run(token, args.channel_id, args.count, args.interval))
    except (discord.DiscordException, OSError) as exc:
        sys.exit(f"Discord エラー: {exc}")
    except KeyboardInterrupt:
        print("\nテストを中断しました。最後の表示が残ります。")


if __name__ == "__main__":
    main()
