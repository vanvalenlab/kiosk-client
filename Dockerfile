FROM python:3.6-slim-buster

WORKDIR /usr/src/app

ENV FILE \
    COUNT \
    MODEL \
    API_HOST="frontend:8080" \
    PREPROCESS="" \
    POSTPROCESS="" \
    UPLOAD_PREFIX="uploads" \
    EXPIRE_TIME="3600" \
    LOG_LEVEL="DEBUG" \
    NUM_CYCLES="1"

COPY requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY . .

ENTRYPOINT ["./bin/entrypoint.sh"]
