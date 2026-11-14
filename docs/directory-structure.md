# ディレクトリ構成案

```text
pokemon_automation/
├── controller/
│   └── switch_arduino_micro/    # Switch用Arduinoファームウェア
│       ├── switch_arduino_micro.ino
│       ├── src/
│       │   ├── SwitchJoystick.cpp
│       │   ├── SwitchJoystick.h
│       │   └── LICENSE-SwitchJoystick
│       ├── build.sh
│       └── upload.sh
│
├── automation/                  # タイトル共通
│   ├── ports/                   # アプリケーションが使うインターフェース
│   │   ├── controller.py
│   │   ├── capture.py
│   │   ├── status.py
│   │   └── review.py
│   └── adapters/                # インターフェースの実装
│       ├── serial_controller.py
│       ├── opencv_capture.py
│       ├── console_review.py
│       └── discord/
│           ├── client.py
│           ├── status.py
│           └── review.py
│
├── title/
│   ├── BDSP/
│   │   ├── application/         # 周回の流れ
│   │   ├── domain/              # 判定結果など
│   │   ├── gameplay/            # BDSP共通の操作・リセット手順
│   │   ├── pokemon/             # ポケモンごとの処理
│   │   │   └── arceus/
│   │   │       ├── encounter.py # 遭遇手順
│   │   │       └── classify.py  # 色判定
│   │   ├── main.py              # 設定・実装の組み立て
│   │   ├── tests/
│   │   └── README.md
│   └── SWSH/                    # 将来追加
│
├── tools/                       # 共通部品の単独動作確認
├── docs/
├── .env.example
├── .env                         # Git管理外
└── README.md
```

```text
周回処理 → ports ← adapters
               ↑
        main.py が実装を渡す（DI）
```
