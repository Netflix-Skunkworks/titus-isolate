FROM ubuntu:16.04
RUN apt update && apt install -y \
    debhelper \
    debmake \
    dh-python \
    dh-systemd \
    dh-virtualenv \
    libsystemd-dev \
    python3-all \
    python3-pip
COPY build-deb.sh /
COPY rules /
COPY titus-isolate.preinst /
COPY titus-isolate.service /
WORKDIR /src
CMD ["/build-deb.sh"]
