FROM python:3.9

COPY pyproject.toml ./main.py /app/
COPY ./jcalapi /app/jcalapi
RUN pip install /app

ENV DEBUG=False \
    LOG_LEVEL=INFO \
    WORKERS=2 \
    HOST=0.0.0.0 \
    PORT=8000

ENV CONFLUENCE_URL= \
    CONFLUENCE_USERNAME= \
    CONFLUENCE_PASSWORD= \
    EXCHANGE_USERNAME= \
    EXCHANGE_PASSWORD=

RUN adduser --disabled-password --gecos '' jcalapi
USER jcalapi

VOLUME ["/config"]
WORKDIR /app
EXPOSE 8000
ENTRYPOINT ["python", "/app/main.py"]
