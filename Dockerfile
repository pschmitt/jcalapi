FROM python:3.9

COPY pyproject.toml ./main.py /app/
COPY ./jcalapi /app/jcalapi
RUN pip install /app

ENV CONFLUENCE_URL= \
    CONFLUENCE_USERNAME= \
    CONFLUENCE_PASSWORD= \
    EXCHANGE_USERNAME= \
    EXCHANGE_PASSWORD=

VOLUME ["/config"]
WORKDIR /app
EXPOSE 8000
ENTRYPOINT ["python", "/app/main.py"]
