FROM gcc:12-bookworm

ARG TASK_VERSION=v3.45.4
ENV TZ=Asia/Tokyo \
    LANG=C.UTF-8 \
    PATH=/home/dev/.local/bin:${PATH}

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git gh ripgrep sudo python3 python3-pip python3-venv \
    gcc-avr avr-libc avrdude make clang-format cppcheck gdb nodejs npm \
    && rm -rf /var/lib/apt/lists/* \
    && arch="$(dpkg --print-architecture)" \
    && case "$arch" in amd64|arm64) ;; *) exit 1 ;; esac \
    && curl -fsSL "https://github.com/go-task/task/releases/download/${TASK_VERSION}/task_linux_${arch}.tar.gz" | tar -xz -C /usr/local/bin task \
    && curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR=/usr/local/bin sh \
    && npm install -g @openai/codex \
    && groupadd -g 1000 dev && useradd -m -u 1000 -g dev -s /bin/bash dev \
    && mkdir -p /home/dev/src /home/dev/.arduino15 /home/dev/Arduino \
    && chown -R dev:dev /home/dev

COPY --chown=dev:dev .devcontainer/infra/arduino/.bashrc /home/dev/.bashrc
USER dev
WORKDIR /home/dev/src
RUN curl -fsSL https://claude.ai/install.sh -o /tmp/install-claude.sh \
    && bash /tmp/install-claude.sh && rm /tmp/install-claude.sh \
    && arduino-cli core update-index && arduino-cli core install arduino:avr \
    && task --version && codex --version && claude --version && gh --version && arduino-cli version
