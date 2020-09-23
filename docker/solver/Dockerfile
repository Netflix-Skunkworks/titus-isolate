FROM dockerregistry.test.netflix.net:7002/engtools/bionicbase

HEALTHCHECK --interval=1m --timeout=3s CMD curl -f $EC2_LOCAL_IPV4 || exit 1
LABEL "com.netflix.titus.systemd"="true"
ENV container docker
ENV DEBIAN_FRONTEND noninteractive

RUN apt update && apt install -y \
    dbus \
    systemd \
    locales \
    curl \
    build-essential \
    git \
    gunicorn3 \
    nginx \
    python3-all \
    python3-dev \
    python3-pip \
    python3-setuptools \
    ssh

RUN apt-get clean && \
    rm -rf /var/lib/apt/lists/*

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US.UTF-8
ENV LC_ALL en_US.UTF-8

RUN python3 --version

RUN pip3 install wheel

COPY prerequirements.txt .
RUN pip3 install -r prerequirements.txt

COPY requirements.txt .
COPY titus-isolate-0.SNAPSHOT.tar.gz .

RUN pip3 install -r requirements.txt
ENV PYTHONPATH="/usr/local/lib/python3.6/dist-packages:/opt/gurobi900/linux64/lib/python3.5_utf32"

COPY gurobi9.0.0_linux64.tar.gz /opt
WORKDIR /opt
RUN tar xf gurobi9.0.0_linux64.tar.gz
WORKDIR /
ENV GUROBI_HOME="/opt/gurobi900/linux64"
COPY init_900.py /opt/gurobi900/linux64/lib/python3.5_utf32/gurobipy/__init__.py

ENV PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/gurobi900/linux64/bin"
ENV LD_LIBRARY_PATH="/opt/gurobi900/linux64/lib"

# Don't start any optional services except for the few we need.
RUN find /etc/systemd/system \
    /lib/systemd/system \
    -path '*.wants/*' \
    -not -name '*journald*' \
    -not -name '*systemd-tmpfiles*' \
    -not -name '*systemd-user-sessions*' \
    -exec rm \{} \;

RUN systemctl set-default multi-user.target

STOPSIGNAL SIGRTMIN+3

COPY root /
RUN systemctl enable nflx-config.service
RUN systemctl enable gunicorn.socket
RUN systemctl enable gunicorn.service
RUN systemctl enable nginx.service

CMD ["/lib/systemd/systemd", "--log-level=debug", "--log-target=journal"]
