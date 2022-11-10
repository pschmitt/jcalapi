FROM python:3.9

COPY pyproject.toml ./main.py /app/
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
    EXCHANGE_USERNAME= \
    EXCHANGE_PASSWORD=

RUN adduser --disabled-password --gecos '' jcalapi
USER jcalapi

VOLUME ["/config"]
WORKDIR /app
EXPOSE 7042
ENTRYPOINT ["python", "/app/main.py"]
