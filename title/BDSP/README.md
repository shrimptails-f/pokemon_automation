# Switch 操作の確認

Arduino Micro とキャプチャー映像を使い、アルセウスとの遭遇、色判定、再起動を試すための手順です。

## 配線とコントローラーの切り替え

Arduino Micro、SH-U09C、Switch ドック、キャプチャー機器の接続と、手動コントローラーとの切り替えは [Arduino Micro の配線・操作手順](../../controller/switch_arduino_micro/README.md) を参照してください。

## ビルドと書き込み

Dev Container 内で `./controller/switch_arduino_micro/build.sh` を実行するとコンパイルを確認できます。書き込みは Arduino を PC に接続して Windows から WSL に USB 接続した上で、WSL ホストから次を実行します。ポートは実際のものに置き換えてください。

```sh
./controller/switch_arduino_micro/upload.sh /dev/ttyACM0
```

このスクリプトは Switch 向けの USB 識別情報を指定します。書き込み後は通常のシリアルポートとして認識されない場合があります。再書き込み時にポートが見つからない場合は、Arduino のリセットボタンを素早く 2 回押してブートローダーを起動し、一時的に現れるポートを指定してください。タイミングによっては再試行が必要です。

## Windows から WSL のソースを使う

WSL にある作業ディレクトリは、Windows の PowerShell から `\\wsl.localhost\<ディストリビューション名>\<WSL 内のパス>` で参照できます。Windows 側に別途リポジトリをクローンする必要はありません。次は WSL の `Ubuntu` にある `/home/user/git_wsl/pokemon_automation` の例です。自分のディストリビューション名とパスに合わせてください。

```powershell
$repo = "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation"
Test-Path "$repo\title\BDSP\review_loop.py"
python "$repo\title\BDSP\review_loop.py" COM8 --device 0 --pokemon giratina --reset-first --discord --debug
```

`Test-Path` が `True` であることを確認してください。Python とパッケージは Windows 側に用意し、COM ポートと映像デバイス番号は使用する機器に合わせます。`--reset-first` はゲームを起動中の画面から使用します。初回は画面を見ながら確認し、途中で止める場合は Ctrl+C を押してください。

Dev Container の `/home/dev/src` と WSL 側のディレクトリが同じ作業場所か分からない場合は、WSL 側に目印を作り、コンテナから読めるか確認できます。PowerShell で次を実行します。

```powershell
wsl -d Ubuntu -- bash -c 'echo from-wsl-123 > /home/user/git_wsl/pokemon_automation/.mount-check-wsl'
```

次に Dev Container のターミナルで確認し、目印を削除します。`from-wsl-123` が表示されれば同じファイルを参照しています。見つからなければパスやマウント設定を確認してください。

```bash
cat /home/dev/src/.mount-check-wsl
rm /home/dev/src/.mount-check-wsl
```

同じディレクトリの場合、コンテナでの編集・Git の更新は Windows から参照するファイルにも反映されます。PC 側と Arduino 側で通信方式が一致するよう、ファームウェアの更新が必要な変更を取り込んだ場合は [書き込み手順](../../docs/windows-arduino-upload.md) に従って更新してください。

## Arduino の通信診断

診断対応ファームウェアを書き込んだ Arduino を通常どおり Switch と SH-U09C に接続し、周回を停止してから Windows の PowerShell で実行します。`COM8` は SH-U09C のポートです。

```powershell
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\tools\controller_diagnostics.py" COM8
```

Arduino 起動後の正常な要求数、破棄した行数、応答の送信試行数、最後に受け付けた時間指定操作のセッション・番号・状態が表示されます。要求数には診断要求も含まれ、応答の送信試行数には今回の診断応答は含まれません。再送はそれぞれ１回ずつ数えます。カウンターは上限で停止し、Arduino を再起動すると消えます。診断要求はセッションや入力状態を変更せず、リースも更新しません。

応答の送信試行数は Arduino が送ろうとした回数であり、PC に届いたことを保証しません。診断コマンドやその応答も通信不良で届かない場合があります。エラーのセッション・番号と最後に受け付けた時間指定操作が一致し、状態が `DONE` なら Arduino は解放の USB 送信成功まで確認していますが、Switch やゲームでの反映は別途確認してください。最後の操作が上書きされた場合や Arduino が再起動した場合は過去の結果を判定できません。

## ボタンを１回だけ操作する

Windows の PowerShell で、現在の Arduino ファームウェアにボタンを１回送れます。周回プログラムを停止してから実行し、`COM8` は SH-U09C のポートに置き換えてください。

```powershell
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\tools\send_control.py" COM8 A
```

末尾を `HOME` や `B`、`UP` などに変えると別の操作を送れます。スティックを上に 500 ms 倒す場合は、末尾を `STICK_UP 500` にします。指定できる操作は `--help` で確認できます。画面が意図しない状態の場合は手動で戻してから実行してください。

## Windows から操作

Windows に Python を用意し、PowerShell で次を実行します。COM ポートはデバイスマネージャーで SH-U09C のものを確認してください。

```powershell
py -m pip install pyserial
py tools/control.py COM5
```

接続できたら Switch の HOME 画面で `LEFT`、`RIGHT` などを入力して確認します。`A`、`B`、`X`、`Y`、`L`、`R`、`ZL`、`ZR`、`PLUS`、`MINUS`、`HOME`、`CAPTURE`、`UP`、`DOWN`、`LEFT`、`RIGHT` が使えます。`quit` で終了します。各入力は約 150 ms 押してから離します。まずゲーム外で操作し、反応を確認してください。

Arduino と PC の通信は 115200 baud、8N1、改行区切りです。`PING` に `PONG`、ボタン名に `OK` を返します。不明な指示には `ERR` を返します。

## 同梱コード

`controller/switch_arduino_micro/src` は [Arduino SwitchJoystick Library](https://github.com/squirelo/Arduino-JoyCon-Library-for-Nintendo-Switch) の commit `459b332cf47e08c030d16887b94d45141a13d268` から取得しました。スケッチ内でビルドできるようヘッダーの include を相対パスに変更しています。ライセンスは `controller/switch_arduino_micro/src/LICENSE-SwitchJoystick` を参照してください。

## キャプチャー映像の確認

Switch ドックの HDMI 出力をキャプチャー機器に接続し、機器の USB を Windows PC に接続します。OBS などで同じ機器を使用している場合は、映像が取得できないことがあるため終了してください。

Windows の PowerShell で次を実行します。`python` の代わりに `py` を使える環境では `py` に置き換えてください。

```powershell
python -m pip install opencv-python
撮影の確認には、下記の遭遇撮影コマンドを使用してください。
```

WSL のディストリビューション名・ユーザー名・リポジトリの場所は実際の環境に合わせます。映像が別のカメラの場合や開けない場合は `--device 1`、`--device 2` のように番号を変えて試してください。

映像ウィンドウを選択し、`S` キーでその時点の画像を PNG 形式で Windows の `ピクチャ\BDSP-captures` に保存します。保存先と解像度は PowerShell に表示されます。`Q` または `Esc` で終了します。保存した画像はリポジトリには入りません。この段階では画像判定や Switch の自動操作は行いません。

## 遭遇直前から前進して撮影

左スティックを上に倒して遭遇できる位置・向きでセーブした状態を想定します。`encounter_capture.py` は一度だけ前進し、指定した時間を待って A を1回押した後、映像を一定間隔で連続保存します。ゲームの再起動は行いません。撮影後に試験的な色判定を行います。移動時間・撮影開始時間はセーブ位置と環境に合わせて調整が必要です。

この機能には `STICK_UP` コマンドを追加した Arduino ファームウェアの書き込みが必要です。Windows からの書き込みは [手順](../../docs/windows-arduino-upload.md) に従い、最新のソースをコピーして再コンパイルしてください。書き込み後、Arduino を Switch に、SH-U09C を Windows に接続します。

Windows で `python -m pip install pyserial opencv-python` を実行し、キャプチャーを使用中の OBS やプレビューを閉じてから、次を実行します。

```powershell
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\title\BDSP\encounter_capture.py" COM8 --device 0 --move-ms 500 --a-after 15 --delay 3 --duration 5 --interval 0.5
```

`COM8` と `--device` は使用中の機器に合わせます。`--move-ms 500` は左スティックを上に 500ms 倒す例で、実際の必要時間ではありません。`--a-after 15` も仮の値です。鳴き声の表示が現れるまでの時間を実機で確認して設定してください。前進終了から `--a-after` 秒後に A を押し、A を離してから `--delay` 秒後に撮影を始め、`--duration` 秒間、`--interval` 秒ごとに PNG を保存します。初回は戦闘になっても構わない状態で試し、セーブ位置、向きと時間を調整してください。画像は Windows のピクチャ内 `BDSP-captures` に実行ごとのフォルダーを作成して保存します。3 秒の開始待機中は Ctrl+C で中止できます。

## 画像を確認して遭遇を繰り返す

`review_loop.py` は撮影後に停止します。保存画像が通常色と確認できた場合に限り `reset` と入力すると、`HOME → X → A → A → A`、14.5 秒待機、`A → A → A`（間隔 2 秒）、7 秒待機の後に次の遭遇を試みます。最初の `HOME → X → A → A → A` の間隔は 1.5 秒です。Enter のみ、または Ctrl+C で停止します。各ボタン間隔は仮の設定で、再起動時の画面遷移は検出しません。最初は実機の画面を見ながら確認してください。`--auto-reset` を付けると通常色の可能性と判定した場合は自動で再起動します。判定不能なら画像確認を待ち、`reset` で再起動して自動ループに戻り、Enter で終了します。色違いの可能性がある場合は停止します。判定は実験段階で、色違いを通常色と誤判定する可能性があります。

```powershell
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\title\BDSP\review_loop.py" COM8 --device 0 --move-ms 500 --a-after 15
```

`--a-after` は鳴き声の表示が出るまでの時間に合わせます。撮影は A を離してから 4.5 秒後に始まり、0.25 秒間隔で 1.5 秒間続きます。`reset` 後はゲームを終了するため、必要なセーブを事前に済ませてください。

途中で止めた後など、最初の遭遇の前にゲームを終了・再起動したい場合は `--reset-first` を追加します。ゲームを起動中の画面から使い、HOME メニューでは実行しないでください。未保存の進行は失われます。再起動時の画面遷移は検出しないため、初回は実機で確認してください。Discord モードでも使用できます。

## Discord 通知の単独テスト

Switch を操作せず、Discord にテストメッセージを 1 件送信します。Bot をサーバーに追加し、対象チャンネルで「チャンネルを見る」と「メッセージを送信」を許可してください。Discord のユーザー設定で「詳細設定」→「開発者モード」を有効にし、通知先チャンネルを右クリックして「チャンネル ID をコピー」します。

Windows の PowerShell で、トークンとチャンネル ID を自分のものに置き換えて実行します。Bot トークンは秘密情報です。チャットやリポジトリに貼らないでください。

```powershell
$env:DISCORD_BOT_TOKEN = Read-Host "Discord Bot トークン"
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\tools\discord_notify_test.py" ここにチャンネルID
Remove-Item Env:DISCORD_BOT_TOKEN
```

パスは実際の環境に合わせてください。トークンは入力時に画面に表示されます。環境変数はこの PowerShell 内だけで有効です。このテストはテキスト送信のみで、画像の送信や返答の受信、自動操作との連携はまだ行いません。

## Discord ボタンの単独テスト

Switch や自動ループを操作せず、Discord のボタン操作を PC で受け取ります。先に上記の方法で `DISCORD_BOT_TOKEN` を設定し、同じ PowerShell で次を実行します。

```powershell
python -m pip install discord.py
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\tools\discord_button_test.py" ここにチャンネルID
```

Discord に届いたボタンを 5 分以内に押すと、選択とユーザー名・ID が PowerShell に表示されて終了します。押せる人を限定する場合はコマンド末尾に `--user-id 自分のユーザーID` を追加します。ID は開発者モードをオンにして自分のプロフィールからコピーできます。省略するとチャンネルを閲覧できる人が操作できます。途中終了は Ctrl+C です。実行を終了すると古いボタンは受け付けられません。

## Discord スレッドの単独テスト

自動ループを操作せず、指定チャンネルに公開スレッドを作成し、一つのメッセージを 10 秒おきに 3 回更新します。Bot には「チャンネルを見る」「公開スレッドを作成」「スレッドでメッセージを送信」の権限が必要です。スレッドはテスト後も残ります。

```powershell
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\tools\discord_thread_test.py" ここにチャンネルID
```

`discord.py` と `DISCORD_BOT_TOKEN` の準備はボタンテストと共通です。途中終了は Ctrl+C です。中断や通信断時は最後の表示が残るため、更新時刻で確認してください。

## Discord で画像を確認しながら周回

周回中はターミナルの同じ行に、現在の周回数と撮影・リセット・画像確認待ちなどの状態を表示します。実行ごとのログは `--output` 配下の `logs/review_*.log` に保存し、起動時にパスを表示します。判定結果やエラーの詳細はこのログで確認できます。`--debug` を付けると Arduino の詳細な通信ログも記録します。Arduino への接続は Discord スレッド作成前に行い、周回終了まで維持します。

`review_loop.py` に `--discord` を付けると、開始時にスレッドを作り、状況メッセージを更新します。画像確認が必要な回だけ指定ユーザーをメンションして画像とボタンを送り、返答を時間制限なく待ちます。「停止」ではリセットしません。通信や送信に失敗した場合も停止します。通信断やPC終了時は最後の状況表示が残るため、更新時刻を確認してください。再起動すると新しいスレッドを作成し、古いボタンは使用できません。

1. Windows で `python -m pip install pyserial opencv-python discord.py python-dotenv` を実行します。
2. リポジトリ直下の `.env.example` を同じ場所に `.env` という名前でコピーし、Bot トークン、チャンネル ID、操作を許可する自分のユーザー ID を記入します。従来の `title/BDSP/.env` も読み込めます。環境変数、直下の `.env`、従来の `.env` の順に優先されます。`.env` は Git の管理対象外です。トークンを他人に共有しないでください。
3. Bot にチャンネル表示、公開スレッドの作成、スレッドでのメッセージ送信、ファイル添付の権限を設定します。
4. 次を実際のパスや機器に合わせて実行します。

```powershell
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\title\BDSP\review_loop.py" COM8 --device 0 --move-ms 500 --a-after 15 --discord
```

この例では毎回画像確認を待ちます。`--auto-reset` を追加すると、通常色の可能性と判定した回は画像を削除して自動リセットし、色違い候補と判定不能だけ確認を待ちます。自動判定は実験段階であり、色違いを誤ってリセットする可能性があります。再起動の画面遷移も検出しないため、最初は実機を見ながら試してください。

## 色の自動判定（試験中）

撮影後、A 入力から約 5.0〜5.4 秒の画像を2枚以上調べ、顔付近の暗さと首元の白・黄色の割合から `通常色の可能性`、`色違いの可能性`、`判定不能` を表示します。実機の色違いではまだ検証していません。保存画像を必ず確認してください。`review_loop.py` は既定では人が `reset` を入力したときだけ再起動します。`--auto-reset` を指定すると通常色の可能性で自動再起動し、その回の保存画像を削除します。判定不能なら画像を残して `reset` の入力を待ちます。色違いの可能性がある場合も画像を残して停止します。手動確認モードでは画像を残します。誤判定によって色違いを失う可能性があるため、設定前に承知してください。

保存済みの実行フォルダーを判定する場合:

```powershell
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\title\BDSP\pokemon\arceus\classify.py" "C:\Users\shrim\Pictures\BDSP-captures\encounter_YYYYMMDD_HHMMSS_xxxxxx"
```

### 構成とテスト

周回処理は `title/BDSP/application`、操作手順は `gameplay` と `pokemon/arceus`、ハードウェアや通知の実装は `automation/adapters` にあります。`automation/ports` の Protocol を満たすテストダブルに差し替えられます。リポジトリのルートから `python -m title.BDSP.main` でも起動できます。

```sh
python -m unittest title.BDSP.tests.test_loop
python -m unittest title.BDSP.tests.test_classify
```

### CI と並列テスト

GitHub Actions では Python テストと Arduino のビルドを別々のワークフローで実行します。Python テストは pytest-xdist で並列実行します。手元ではリポジトリのルートから次のように実行できます。

```sh
python -m pip install -r requirements-test.txt
python -m pytest -n auto title/BDSP/tests
```

## ギラティナの目の前から遭遇・確認

ギラティナの正面でセーブし、話しかけられる位置から開始します。A を押し、既定で 3 秒後にもう一度 A を押します。2回目の A から既定で 8.2〜16.0 秒の間に、約0.067秒（1/15 秒）間隔で117枚を保存します。時間内に必要な枚数を撮れなかった場合はエラーで停止します。初回は画面を見て、A の間隔と戦闘画面が撮れていることを確認してください。

```powershell
python "\\wsl.localhost\Ubuntu\home\user\git_wsl\pokemon_automation\title\BDSP\review_loop.py" COM8 --device 0 --pokemon giratina
```

既定では画像保存後に確認待ちになります。通常色を確認した場合だけ `reset` と入力すると、既存の再起動手順を実行して次の遭遇へ進みます。Enter で停止します。`--discord` も利用できます。ギラティナの構図に近い画像を選んで色を判定します。通常色の判定には登場セリフも確認します。構図が一致しない画像に水色がある場合、手持ちを出すセリフと確認できなければ判定不能として確認待ちになります。ギラティナの色判定は試験段階です。通常色3回分と YouTube の色違い参考画像3枚で確認しましたが、実機の色違いでは未検証です。`--auto-reset` を指定すると通常色と判定した場合に自動リセットするため、誤判定で色違いを失う可能性があります。判定不能や色違い候補では確認待ちになります。A の間隔は `--a-after`（秒）で調整できます。撮影範囲は `--capture-delay`、`--capture-duration`、`--capture-interval`（秒）で変更できます。再起動は画面遷移を検出しないため、初回は実機で確認してください。

### 色違い音声の試験

ギラティナ周回では、体色と連続画像の発光を調べ、どちらかが候補なら確認待ちになります。発光検出は「ギラティナが現れた！」の表示が消えた後の最大 2 秒を対象にします。色違いでは引きの画面に切り替わってから光るため、画面が大きく切り替わったら比較の基準を取り直して続け、「いっておいで」の表示が出たら打ち切ります（ボールの光を発光と区別するため）。短時間で切り替わっても、必要な画像が連続して撮影され、続く「いっておいで」の表示を確認でき、発光がなければ発光候補なしとします。セリフ未検出、撮影不足、不明な画面切り替えなどは判定不能として確認待ちになります。撮影時間の既定値は 7.8 秒です。`sparkle_diagnostics.csv` に対象画像の発光候補の数値を保存します。発光検出は試験段階で、誤検出や見逃しの可能性があります。

各遭遇のフォルダーに `encounter.mp4` も保存します。2 回目の A 入力後から撮影終了までの映像を約 10 fps で記録し、音声判定が有効な場合は録音した音声も含めます。音声と映像の同期は概算です。`--auto-reset` で通常色と判定した回は、画像と同じくフォルダーごと動画も削除します。確認待ちになった回や手動確認の回は残ります。

録画した動画に検査範囲と各フレームの数値を重ねて確認できます。隣に同じ数値の CSV も作成します。

```powershell
python -m title.BDSP.pokemon.giratina.sparkle_debug "入力動画.mp4" "確認動画.mp4"
```

音声も併用するには後述の依存関係をインストールし、周回コマンドに次を追加します。

参照音を用意するときは、ゲームの音量設定で BGM とポケモンの鳴き声を 0 にし、効果音を残して録音します。色違いのきらめきが鳴る区間を確認し、その開始秒と終了秒を指定してください。周回時も同じ音量設定と入力経路を使います。以下の 12 秒と 14 秒は指定例です。この録音方法は [Pokétools の固定リセット手順](https://github.com/fdekeers/poketools#stationary-pok%C3%A9mon-shiny-reset) を参考にしています。

```powershell
--audio-reference "参照動画.mp4" --audio-start 12 --audio-end 14 --audio-device 0
```

実機で録音した色違いギラティナのきらめき音を `title/BDSP/pokemon/giratina/templates/shiny_sound.wav` に同梱しています（BGM・鳴き声 0、16 kHz モノラル、1.8 秒）。`--audio-reference` を省略して `--audio-device` だけを指定すると、この音全体を参照にします。

```powershell
--audio-device 0
```

`--audio-reference` を指定した場合の `--audio-start` と `--audio-end` の既定値は 12 秒と 14 秒です。

入力デバイス番号は `python -m sounddevice` で確認します。参照区間と相関しきい値 `--audio-threshold`（既定 0.5）は環境に合わせて調整してください。音声でも候補を検出すると確認待ちになります。音声入力の失敗・無音時は操作を停止します。音声判定はギラティナで `--audio-device` か `--audio-reference` を指定したときだけ有効です。録音は撮影終了時に止め、動画開始以降を照合します。表示する音声相関の時刻は動画開始からのおおよその秒数です。同梱の参照音は実機の色違い 1 回分の録音から作ったもので、別の色違い遭遇での検出は未検証です。自動リセットの安全性は保証できません。

録画済みファイルを使い、独立した試験ツールで音声照合を確認することもできます。参照動画と照合対象は各自で用意してください。リポジトリのルートで依存関係をインストールし、例えば次のように実行します。

```powershell
python -m pip install -r title/BDSP/requirements-audio.txt
python -m title.BDSP.pokemon.giratina.shiny_audio --reference "参照動画.mp4" --start 12 --end 14 --input "照合動画.mp4"
```

`--start` と `--end` は参照動画の秒数です。録音して照合するには `--input` の代わりに `--record 20 --device 0` のように指定します。入力デバイス番号は `python -m sounddevice` で確認してください。録音開始後に遭遇させてください。既定のしきい値 0.5 は仮値で、音量や BGM、鳴き声、録音環境により見逃しや誤検出が起こります。参照区間には色違い音以外も含まれるため、通常色と色違い両方の別録音を使って区間としきい値を調整する必要があります。
