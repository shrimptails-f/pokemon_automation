# 開発環境

WSL の `~/git_wsl/pokemon_automation` を VS Code で開き、Dev Containers: Reopen in Container を実行する。設定や Dockerfile を変更したら Dev Containers: Rebuild Container を実行する。初回ビルドでは Arduino AVR core と開発ツールのダウンロードが必要。

コンテナ内で `task doctor` で確認し、`task codex` または `task claude` で各 CLI を起動できる。Arduino のスケッチが用意できたら `arduino-cli compile -b arduino:avr:micro <スケッチのディレクトリ>` でコンパイルする。

Arduino の USB 書き込みはベースの `write_program.sh` を WSL ホスト上で使う。Arduino を Windows から WSL に接続する方法はルートの README を参照。コンテナには USB デバイスを公開していない。Windows の OBS 画面取得と SH-U09C の COM ポート制御は Windows 側で動かす想定で、コンテナから直接アクセスしない。

WSL ホストの `~/.codex`、`~/.claude`、`~/.claude.json` をコンテナに読み書き可能で共有する。認証に加え設定や履歴も共有され、コンテナ側の変更がホストに反映される。ホスト側で認証していない場合は各 CLI でログインする。Git 設定は読み取り専用で共有する。Arduino core とライブラリは Docker ボリュームに保存され、再構築後も残る。イメージの core を更新しても既存ボリュームには反映されないため、必要に応じコンテナ内で `arduino-cli core update-index` と `arduino-cli core upgrade` を実行する。
