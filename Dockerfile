FROM dockerregistry.test.netflix.net:7002/engtools/xenialbase:latest

RUN apt-get update && \
    apt-get install -y nflx-python-{{.ToolVersions.python}} && \
    /apps/python{{.ToolVersions.python}}/bin/python -m pip install virtualenv && \
    /apps/python{{.ToolVersions.python}}/bin/python -m virtualenv /apps/titusjob

COPY . /apps/titusjob
WORKDIR /apps/titusjob

RUN /apps/titusjob/bin/pip install --no-cache-dir -r requirements.txt
CMD ["sh", "-c", "/apps/titusjob/bin/python ./run.py --package-count ${PACKAGE_COUNT} --cores-per-package ${CORES_PER_PACKAGE} --threads-per-core ${THREADS_PER_CORE}"]
