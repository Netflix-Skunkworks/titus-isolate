FROM ubuntu:16.04
RUN apt update && apt install -y \
    debhelper \
    debmake \
    dh-python \
    python3-all \
    dh-virtualenv \
    python3-pip
COPY rules /rules
COPY build-deb.sh /build-deb.sh
WORKDIR /src
CMD ["/build-deb.sh"]
