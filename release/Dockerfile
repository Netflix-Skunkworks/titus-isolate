FROM ubuntu:16.04
RUN apt update && apt install -y \
    debhelper \
    debmake \
    dh-python \
    dh-systemd \
    dh-virtualenv \
    git \
    libsystemd-dev \
    python3-all \
    python3-pip \
    ssh
COPY build-deb.sh /
COPY rules /
COPY titus-isolate.service /
COPY titus-isolate.socket /
WORKDIR /src
CMD ["/build-deb.sh"]
