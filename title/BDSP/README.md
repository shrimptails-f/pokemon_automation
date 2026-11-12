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
