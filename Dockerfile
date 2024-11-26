FROM python:3.9-bookworm

ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive
ENV LANG=C.UTF-8

RUN apt-get update -qq && apt-get -y upgrade && apt-get install -y -qq \
    # std libs
    git less nano curl \
    ca-certificates \
    wget build-essential\
    # python basic libs
    gettext \
    # geodjango
    gdal-bin binutils libproj-dev libgdal-dev \
    # postgresql
    libpq-dev postgresql-client && \
    apt-get clean all && rm -rf /var/apt/lists/* && rm -rf /var/cache/apt/*
RUN mkdir -p /code/src

RUN useradd -ms /bin/bash django
RUN chown -R django:django /code
COPY entrypoint.sh /usr/local/bin/entrypoint.sh

USER django

RUN python3.9 -m venv /code/venv
RUN  /code/venv/bin/pip install --no-cache-dir pip setuptools wheel -U

COPY . /code/src
WORKDIR /code/src

# Install dev requirements
RUN /code/venv/bin/pip3 install --no-cache-dir -e .[dev] -U

ENTRYPOINT ["/bin/sh", "-e", "/usr/local/bin/entrypoint.sh"]
