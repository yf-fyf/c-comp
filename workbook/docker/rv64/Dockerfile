FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        file \
        gdb-multiarch \
        gcc \
        gcc-riscv64-linux-gnu \
        libc6-dev-riscv64-cross \
        binutils-riscv64-linux-gnu \
        git \
        make \
        python3 \
        qemu-user \
        qemu-user-static \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
