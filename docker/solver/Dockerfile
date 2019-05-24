FROM dockerregistry.test.netflix.net:7002/engtools/xenialbase

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
COPY titus-isolate-0.SNAPSHOT.tar.gz .
COPY cvxpy-1.0.21.tar.gz .

RUN pip3 install -r requirements.txt
ENV PYTHONPATH="/usr/local/lib/python3.5/dist-packages:/opt/gurobi811/linux64/lib/python3.5_utf32"

COPY gurobi8.1.1_linux64.tar.gz /opt
WORKDIR /opt
RUN tar xf gurobi8.1.1_linux64.tar.gz
WORKDIR /
ENV GUROBI_HOME="/opt/gurobi810/linux64"

ENV PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/gurobi810/linux64/bin"
ENV LD_LIBRARY_PATH="/opt/gurobi811/linux64/lib"

HEALTHCHECK --interval=1m --timeout=3s CMD curl -f $EC2_LOCAL_IPV4 || exit 1
CMD gunicorn -w $TITUS_NUM_CPU -b $EC2_LOCAL_IPV4:80 --log-level=info --worker-tmp-dir /dev/shm titus_isolate.api.solve:app
