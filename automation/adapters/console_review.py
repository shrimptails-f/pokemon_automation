class ConsoleReview:
    def should_reset(self, result):
        return input("画像を確認し、通常色なら reset、停止するなら Enter: ").strip().lower() == "reset"


class ConsoleStatus:
    def update(self, attempt, state):
        print(f"{attempt}回目: {state}", flush=True)
