# Switch 操作の確認

Arduino Micro を Switch の有線コントローラーとして動作させ、Windows から SH-U09C 経由でボタンを 1 回ずつ送るための試作です。色違い判定や自動リセットは行いません。実機での互換性は未確認です。

## 配線

電源を切った状態で接続します。SH-U09C の信号電圧を Arduino Micro の 5V ロジックに合わせてください。製品のピン表示を確認し、VCC は接続しません。

| SH-U09C | Arduino Micro |
| --- | --- |
| TX | 0 / RX |
| RX | 1 / TX |
| GND | GND |

書き込み後、Arduino の USB を Switch ドックに、SH-U09C の USB を Windows PC に接続します。Arduino は Switch 側から給電されます。Switch の設定で「Proコントローラーの有線通信」を ON にして試してください。

## Arduino で操作する前の手順（確認した環境）

ほかのコントローラーを Switch に接続していない状態から始めます。

1. Arduino Micro の USB を Switch ドックに接続する。
2. SH-U09C の USB を Windows PC に挿し直す。
3. Windows から Arduino にボタンを送り、Switch が反応することを確認する。

Arduino と SH-U09C の TX・RX・GND は配線しておきます。上記は手元の機材で確認した手順です。ほかのコントローラーの接続状態や環境によっては動作が異なる場合があります。手動操作に戻すための確実な手順は未確認です。

## ビルドと書き込み

Dev Container 内で `./title/BDSP/build.sh` を実行するとコンパイルを確認できます。書き込みは Arduino を PC に接続して Windows から WSL に USB 接続した上で、WSL ホストから次を実行します。ポートは実際のものに置き換えてください。

```sh
./title/BDSP/upload.sh /dev/ttyACM0
```

Switch 向けの USB 識別情報を指定するため、ルートの `write_program.sh` ではなく上記を使います。書き込み後は通常のシリアルポートとして認識されない場合があります。再書き込み時にポートが見つからない場合は、Arduino のリセットボタンを素早く 2 回押してブートローダーを起動し、一時的に現れるポートを指定してください。タイミングによっては再試行が必要です。

## Windows から操作

Windows に Python を用意し、PowerShell で次を実行します。COM ポートはデバイスマネージャーで SH-U09C のものを確認してください。

```powershell
py -m pip install pyserial
py title/BDSP/control.py COM5
```

接続できたら Switch の HOME 画面で `LEFT`、`RIGHT` などを入力して確認します。`A`、`B`、`X`、`Y`、`L`、`R`、`ZL`、`ZR`、`PLUS`、`MINUS`、`HOME`、`CAPTURE`、`UP`、`DOWN`、`LEFT`、`RIGHT` が使えます。`quit` で終了します。各入力は約 150 ms 押してから離します。まずゲーム外で操作し、反応を確認してください。

Arduino と PC の通信は 115200 baud、8N1、改行区切りです。`PING` に `PONG`、ボタン名に `OK` を返します。不明な指示には `ERR` を返します。

## 同梱コード

`controller/src` は [Arduino SwitchJoystick Library](https://github.com/squirelo/Arduino-JoyCon-Library-for-Nintendo-Switch) の commit `459b332cf47e08c030d16887b94d45141a13d268` から取得しました。スケッチ内でビルドできるようヘッダーの include を相対パスに変更しています。ライセンスは `vendor/SwitchJoystick-LICENSE` を参照してください。

## キャプチャー映像の確認

Switch ドックの HDMI 出力をキャプチャー機器に接続し、機器の USB を Windows PC に接続します。OBS などで同じ機器を使用している場合は、映像が取得できないことがあるため終了してください。

Windows の PowerShell で次を実行します。`python` の代わりに `py` を使える環境では `py` に置き換えてください。

```powershell
python -m pip install opencv-python
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\title\BDSP\capture.py" --device 0
```

WSL のディストリビューション名・ユーザー名・リポジトリの場所は実際の環境に合わせます。映像が別のカメラの場合や開けない場合は `--device 1`、`--device 2` のように番号を変えて試してください。

映像ウィンドウを選択し、`S` キーでその時点の画像を PNG 形式で Windows の `ピクチャ\BDSP-captures` に保存します。保存先と解像度は PowerShell に表示されます。`Q` または `Esc` で終了します。保存した画像はリポジトリには入りません。この段階では画像判定や Switch の自動操作は行いません。

## 遭遇直前から前進して撮影

左スティックを上に倒して遭遇できる位置・向きでセーブした状態を想定します。`encounter_capture.py` は一度だけ前進し、指定した時間を待って A を1回押した後、映像を一定間隔で連続保存します。ゲームの再起動や色違い判定は行いません。移動時間・撮影開始時間はセーブ位置と環境に合わせて調整が必要です。

この機能には `STICK_UP` コマンドを追加した Arduino ファームウェアの書き込みが必要です。Windows からの書き込みは [手順](../../docs/windows-arduino-upload.md) に従い、最新のソースをコピーして再コンパイルしてください。書き込み後、Arduino を Switch に、SH-U09C を Windows に接続します。

Windows で `python -m pip install pyserial opencv-python` を実行し、キャプチャーを使用中の OBS やプレビューを閉じてから、次を実行します。

```powershell
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\title\BDSP\encounter_capture.py" COM8 --device 0 --move-ms 500 --a-after 15 --delay 3 --duration 5 --interval 0.5
```

`COM8` と `--device` は使用中の機器に合わせます。`--move-ms 500` は左スティックを上に 500ms 倒す例で、実際の必要時間ではありません。`--a-after 15` も仮の値です。鳴き声の表示が現れるまでの時間を実機で確認して設定してください。前進終了から `--a-after` 秒後に A を押し、A を離してから `--delay` 秒後に撮影を始め、`--duration` 秒間、`--interval` 秒ごとに PNG を保存します。初回は戦闘になっても構わない状態で試し、セーブ位置、向きと時間を調整してください。画像は Windows のピクチャ内 `BDSP-captures` に実行ごとのフォルダーを作成して保存します。3 秒の開始待機中は Ctrl+C で中止できます。

## 画像を確認して遭遇を繰り返す

`review_loop.py` は撮影後に停止します。保存画像が通常色と確認できた場合に限り `reset` と入力すると、`HOME → X → A → A → A`、13 秒待機、`A → A → A`（間隔 2 秒）、7 秒待機の後に次の遭遇を試みます。Enter のみ、または Ctrl+C で停止します。各ボタン間隔は仮の設定で、再起動時の画面遷移は検出しません。最初は実機の画面を見ながら確認してください。`--auto-reset` を付けると通常色の可能性と判定した場合は自動で再起動し、それ以外は停止します。判定は実験段階で、色違いを通常色と誤判定する可能性があります。

```powershell
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\title\BDSP\review_loop.py" COM8 --device 0 --move-ms 500 --a-after 15
```

`--a-after` は鳴き声の表示が出るまでの時間に合わせます。撮影は A を離してから 4.5 秒後に始まり、0.25 秒間隔で 1.5 秒間続きます。`reset` 後はゲームを終了するため、必要なセーブを事前に済ませてください。

## 色の自動判定（試験中）

撮影後、A 入力から約 4.75〜5.4 秒の画像を2枚以上調べ、顔付近の暗さと首元の白・黄色の割合から `通常色の可能性`、`色違いの可能性`、`判定不能` を表示します。実機の色違いではまだ検証していません。保存画像を必ず確認してください。`review_loop.py` は既定では人が `reset` を入力したときだけ再起動します。`--auto-reset` を指定すると通常色の可能性で自動再起動します。誤判定によって色違いを失う可能性があるため、設定前に承知してください。

保存済みの実行フォルダーを判定する場合:

```powershell
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\title\BDSP\classify.py" "C:\Users\shrim\Pictures\BDSP-captures\encounter_YYYYMMDD_HHMMSS_xxxxxx"
```
