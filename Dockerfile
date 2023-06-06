FROM python:3.10

COPY pyproject.toml /app/
COPY ./jcalapi /app/jcalapi

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata && \
    pip install /app && \
    rm -rf /var/lib/apt/lists/*

ENV DEBUG=False \
    LOG_LEVEL=INFO \
    WORKERS=2 \
    HOST=0.0.0.0 \
    PORT=7042

ENV CONFLUENCE_URL= \
    CONFLUENCE_USERNAME= \
    CONFLUENCE_PASSWORD= \
    CONFLUENCE_CONVERT_EMAIL=false \
    EXCHANGE_USERNAME= \
    EXCHANGE_PASSWORD= \
    EXCHANGE_EMAIL= \
    EXCHANGE_AUTO_DISCOVERY=true \
    EXCHANGE_SERVICE_ENDPOINT= \
    EXCHANGE_AUTH_TYPE=NTLM \
    EXCHANGE_VERSION= \
    EXCHANGE_SHARED_INBOXES=

RUN adduser --disabled-password --gecos '' jcalapi
USER jcalapi

VOLUME ["/config"]
WORKDIR /app
EXPOSE 7042
WORKDIR /app
ENTRYPOINT ["python", "/app/jcalapi/run.py"]
