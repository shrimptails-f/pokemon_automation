"""Send a standalone Discord notification without operating the Switch."""
import argparse
import json
import os
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description="Discord にテスト通知を送信")
    parser.add_argument("channel_id", help="通知先の Discord チャンネル ID")
    args = parser.parse_args()
    if not args.channel_id.isascii() or not args.channel_id.isdigit():
        parser.error("チャンネル ID は数字で指定してください")
    token = os.environ.get("DISCORD_BOT_TOKEN", "").strip()
    if not token:
        sys.exit("環境変数 DISCORD_BOT_TOKEN に Bot トークンを設定してください。")
    payload = json.dumps({"content": "BDSP 通知テストです。Discord への送信に成功しました。", "allowed_mentions": {"parse": []}}).encode("utf-8")
    request = Request(
        f"https://discord.com/api/v10/channels/{args.channel_id}/messages",
        data=payload,
        headers={"Authorization": f"Bot {token}", "Content-Type": "application/json",
                 "User-Agent": "DiscordBot (https://github.com/discord/discord-api-docs, 1.0)"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            if response.status != 200:
                sys.exit(f"送信に失敗しました (HTTP {response.status})。")
    except HTTPError as exc:
        sys.exit(f"送信に失敗しました (HTTP {exc.code})。トークン、チャンネル ID、Bot の権限を確認してください。")
    except (URLError, TimeoutError, OSError):
        sys.exit("Discord に接続できませんでした。ネットワーク接続を確認してください。")
    print("テスト通知を送信しました。Discord のチャンネルを確認してください。")


if __name__ == "__main__":
    main()
