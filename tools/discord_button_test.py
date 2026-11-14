"""Test Discord button responses independently of game control."""
import argparse
import asyncio
import os
import sys

try:
    import discord
except ImportError:
    sys.exit("discord.py が必要です: python -m pip install discord.py")


class ChoiceView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.choice = None
        self.message = None

    async def interaction_check(self, interaction):
        if self.user_id and interaction.user.id != self.user_id:
            await interaction.response.send_message("このテストの操作は許可されていません。", ephemeral=True)
            return False
        return True

    async def choose(self, interaction, choice):
        self.choice = choice
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(content=f"テスト結果: {choice}（Switch は操作しません）", view=self)
        print(f"選択: {choice} / ユーザー: {interaction.user} / ID: {interaction.user.id}", flush=True)
        self.stop()

    @discord.ui.button(label="通常色・再開", style=discord.ButtonStyle.primary)
    async def resume(self, interaction, button):
        await self.choose(interaction, "通常色・再開")

    @discord.ui.button(label="停止", style=discord.ButtonStyle.danger)
    async def stop_button(self, interaction, button):
        await self.choose(interaction, "停止")


async def run(token, channel_id, user_id):
    client = discord.Client(intents=discord.Intents.none())
    started = False

    @client.event
    async def on_ready():
        nonlocal started
        if started:
            return
        started = True
        try:
            channel = await client.fetch_channel(channel_id)
            view = ChoiceView(user_id)
            view.message = await channel.send("ボタンの動作テストです。どちらを押しても Switch は操作しません。", view=view)
            print("Discord にボタンを送信しました。5分以内に押してください。", flush=True)
            timed_out = await view.wait()
            if timed_out:
                print("時間切れです。操作は受け付けません。", flush=True)
                for item in view.children:
                    item.disabled = True
                await view.message.edit(content="テストは時間切れになりました。", view=view)
        except discord.DiscordException as exc:
            print(f"Discord エラー: {exc}", file=sys.stderr, flush=True)
        finally:
            await client.close()

    await client.start(token)


def main():
    parser = argparse.ArgumentParser(description="Discord のボタン操作を単独テスト")
    parser.add_argument("channel_id", type=int, help="通知先チャンネル ID")
    parser.add_argument("--user-id", type=int, help="操作を許可するユーザー ID（省略時はチャンネルの閲覧者）")
    args = parser.parse_args()
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        sys.exit("環境変数 DISCORD_BOT_TOKEN に Bot トークンを設定してください。")
    try:
        asyncio.run(run(token, args.channel_id, args.user_id))
    except (discord.DiscordException, OSError) as exc:
        sys.exit(f"Discord への接続に失敗しました: {exc}")
    except KeyboardInterrupt:
        print("\nテストを終了しました。")


if __name__ == "__main__":
    main()
