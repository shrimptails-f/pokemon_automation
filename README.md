# ポケモンの色違い厳選の自動化

Nintendo Switch のゲーム画面を PC に取り込み、Arduino Micro からコントローラー操作を送ることで、ポケモンの色違い厳選を自動化するためのリポジトリです。現在は『ポケットモンスター ブリリアントダイヤモンド・シャイニングパール』のアルセウスを対象にしています。

## 使用する機材

- Nintendo Switch とドック
- Windows PC
- [Arduino Micro](https://www.amazon.co.jp/dp/B00AFY2S56)
- [DSD TECH SH-U09C USB to TTL アダプター](https://www.amazon.co.jp/dp/B07BBPX8B8)
- [Basicolor キャプチャーボード](https://www.amazon.co.jp/dp/B08GS92CG1) など、PC に Switch の映像を取り込める機器
- 接続用の HDMI ケーブル、データ通信に対応した USB ケーブル、ジャンパーワイヤー

Arduino Micro を Switch ドックに接続し、SH-U09C 経由で PC から操作します。Switch の映像はキャプチャー機器を通じて PC に取り込み、遭遇画面の判定に使います。ピンの接続方法や電圧設定、操作するコントローラーの切り替えは [配線・接続手順](controller/switch_arduino_micro/README.md) を参照してください。

## 手順とドキュメント

- [配線・接続手順](controller/switch_arduino_micro/README.md)
- [開発環境の構築](docs/development.md)
- [Windows から Arduino に書き込む](docs/windows-arduino-upload.md)
- [BDSP の操作・色違い厳選](title/BDSP/README.md)
- [ディレクトリ構成](docs/directory-structure.md)
- [ベースリポジトリの環境構築手順（過去の記録）](docs/legacy-setup.md)

色違いの自動判定は画像や撮影条件によって誤る可能性があります。自動リセットの前提と動作は BDSP の手順を確認してください。
