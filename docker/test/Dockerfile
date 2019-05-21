FROM ubuntu:18.04

RUN apt update && apt install -y \
    build-essential \
    git \
    python3-all \
    python3-dev \
    python3-pip \
    python3-setuptools \
    ssh

RUN pip3 install wheel

COPY prerequirements.txt .
RUN pip3 install -r prerequirements.txt

COPY requirements.txt .
RUN pip3 install -r requirements.txt
