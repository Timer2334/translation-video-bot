FROM ubuntu:latest
LABEL authors="Timer2334"

WORKDIR /app

# Обновляем систему и устанавливаем основные инструменты
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y curl gnupg2 software-properties-common lsb-release wget ca-certificates build-essential git
#TODO добавить в самом конце (память экономит) apt-get clean && rm -rf /var/lib/apt/lists/*

# Устанавливаем Python
#apt-get update && \
RUN apt-get install -y python3 python3-pip python3-venv && \
    python3 --version && pip3 --version

# Устанавливаем FFmpeg
RUN apt-get install -y ffmpeg && \
    ffmpeg -version

# Устанавливаем NodeJS
RUN apt-get update && \
    apt-get install -y nodejs && \
    node -v

# Устанавливаем Bun
RUN apt-get update && apt-get install -y \
    curl \
    unzip \
    bash

RUN apt-get install bash && \
    curl -fsSL https://bun.sh/install | bash

RUN /root/.bun/bin/bun -v

# Устанавливаем Telegram Bot API server
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y make git zlib1g-dev libssl-dev gperf cmake clang-18 libc++-18-dev libc++abi-18-dev && \
    git clone --recursive https://github.com/tdlib/telegram-bot-api.git && \
    cd telegram-bot-api && \
    rm -rf build && \
    mkdir build && \
    cd build && \
    CXXFLAGS="-stdlib=libc++" CC=/usr/bin/clang-18 CXX=/usr/bin/clang++-18 cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX:PATH=.. .. && \
    cmake --build . --target install && \
    cd ../.. && \
    ls -l telegram-bot-api/bin/telegram-bot-api*

