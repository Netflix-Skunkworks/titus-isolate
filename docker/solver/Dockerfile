FROM dockerregistry.test.netflix.net:7002/engtools/bionicbase

HEALTHCHECK --interval=1m --timeout=3s CMD curl -f $EC2_LOCAL_IPV4 || exit 1

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

WORKDIR /home/nfsuper
CMD /usr/bin/gunicorn3 -w 4 --log-level=info --worker-tmp-dir /dev/shm titus_isolate.api.solve:app
