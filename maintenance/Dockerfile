FROM python:3.12.12-slim-bookworm@sha256:2986c55feb36e6cae00fa1fefb454283e4b33f35e75ff8bdd123b134130be301 AS fetch
ARG CRICTL_SHA256=83855e114566a8a8c44c548d515670f51de3a5e1da8b2effb59870e2f10c25a3
RUN python -c 'import urllib.request; urllib.request.urlretrieve("https://github.com/kubernetes-sigs/cri-tools/releases/download/v1.36.0/crictl-v1.36.0-linux-amd64.tar.gz", "/tmp/crictl.tar.gz")'
RUN echo "${CRICTL_SHA256}  /tmp/crictl.tar.gz" | sha256sum -c - && tar -xzf /tmp/crictl.tar.gz -C /usr/local/bin crictl
FROM python:3.12.12-slim-bookworm@sha256:2986c55feb36e6cae00fa1fefb454283e4b33f35e75ff8bdd123b134130be301
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TMPDIR=/tmp
COPY --from=fetch /usr/local/bin/crictl /usr/local/bin/crictl
COPY maintenance/node_retention.py retention_guard.py /app/
WORKDIR /app
USER 65532:65532
ENTRYPOINT ["python3", "-B", "/app/node_retention.py"]
