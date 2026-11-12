# Windows から Arduino Micro に書き込む

`title/BDSP/controller` の Switch 操作用プログラムを、Windows の Arduino CLI でコンパイルして書き込む手順です。WSL の USB 自動接続を使った書き込みでは、Arduino のブートローダーへの切り替え後、WSL への再接続が間に合わず失敗したため、Windows から直接書き込みました。

## 準備

1. Arduino Micro をデータ通信用 USB ケーブルで Windows PC に接続する。SH-U09C との配線は外す。
2. `usbipd attach --wsl ... --auto-attach` を使っている場合は、実行中の PowerShell で `Ctrl+C` を押して終了する。必要に応じて Arduino を抜き差しし、Windows 側に戻す。
3. Arduino CLI が Windows にない場合は、PowerShell で `winget install --id ArduinoSA.CLI --exact` を実行する。インストール後は PowerShell を開き直す。
4. 初回は AVR core をインストールする。

```powershell
arduino-cli core update-index
arduino-cli core install arduino:avr
```

ポートを確認する。

```powershell
arduino-cli board list
```

以下は `Arduino Micro` が `COM5` に表示された場合の例。実際に表示されたポートに置き換える。

## Windows にソースをコピー

以下の `$source` は WSL のディストリビューション名が `Ubuntu`、ユーザー名が `user`、リポジトリが `~/git_wsl/pokemon_automation` の例。環境に合わせて変更する。スケッチのフォルダー名は `controller.ino` に合わせて `controller` にする。

```powershell
$source = "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\title\BDSP\controller"; $sketch = "$env:TEMP\bdsp-sketch\controller"; New-Item -ItemType Directory -Force $sketch | Out-Null; Copy-Item -Recurse -Force "$source\*" $sketch; Test-Path "$sketch\controller.ino"
```

`True` が表示されることを確認する。ソースを変更した場合は、再度コピーしてからコンパイルする。

## コンパイル

次のコマンドは Switch 向けの USB 識別情報を指定する。Windows PowerShell の引数処理に合わせ、USB 名の引用符を `\"`、名前中の空白を C 言語のエスケープ表記 `\040` で指定している。

```powershell
arduino-cli compile --fqbn arduino:avr:micro --build-property 'build.vid=0x0F0D' --build-property 'build.pid=0x0092' --build-property 'build.usb_product=\"POKKEN\040CONTROLLER\"' --build-property 'build.usb_manufacturer=\"HORI\040CO.,LTD.\"' --build-property 'build.extra_flags={build.usb_flags}' --output-dir "$env:TEMP\bdsp-build" "$sketch"
```

メモリ使用量が表示され、エラーなく完了したことを確認する。失敗した場合は書き込みに進まず、エラーを解消してから再実行する。

## 書き込み

```powershell
arduino-cli upload --fqbn arduino:avr:micro --port COM5 --input-dir "$env:TEMP\bdsp-build" "$sketch"
```

`COM5` は `board list` で確認した Arduino のポートに置き換える。書き込み時に Arduino はブートローダーとして再接続するため、`New upload port: COM7 (serial)` のように別のポートが表示されることがある。コマンドがエラーなく終了したことを確認する。

書き込み後は Arduino の USB を PC から外して Switch ドックに接続する。SH-U09C との配線および Windows からの操作は [BDSP の README](../title/BDSP/README.md) を参照する。
