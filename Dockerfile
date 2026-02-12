FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt /app/
RUN python -m pip install --upgrade pip \
    && pip install -r requirements.txt

COPY . /app

# default command is a no-op; overridden in docker-compose for each service
CMD ["/bin/sh", "-c", "echo 'Specify the service command in docker-compose' && sleep infinity"]
