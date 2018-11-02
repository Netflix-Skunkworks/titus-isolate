FROM ubuntu:16.04
RUN apt update && apt install -y \
    debhelper \
    debmake \
    dh-python \
    dh-systemd \
    dh-virtualenv \
    python3-all \
    python3-pip
COPY rules /rules
COPY build-deb.sh /build-deb.sh
COPY titus-isolate.service /titus-isolate.service
WORKDIR /src
CMD ["/build-deb.sh"]
