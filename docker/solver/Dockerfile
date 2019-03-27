FROM ubuntu:16.04
RUN apt update && apt install -y \
    python3-all \
    python3-pip
COPY requirements.txt /
COPY prerequirements.txt /
RUN pip3 install -r prerequirements.txt
RUN pip3 install -r requirements.txt
ENV PYTHONPATH="/usr/local/lib/python3.5/dist-packages"
CMD gunicorn -w $TITUS_NUM_CPU -b 127.0.0.1:80 --log-level=info titus_isolate.api.solve:app
