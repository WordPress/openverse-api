#################
# Python builder #
##################

FROM python:3.10 as builder

ENV PYTHONBUFFERED=1
ENV PATH="/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y python3-dev \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /venv \
    && pip install --upgrade pipenv

# Copy the Pipenv files into the container
COPY Pipfile Pipfile.lock ./

RUN pipenv install --system --deploy --dev

####################
# Ingestion server #
####################

FROM python:3.10-slim as ingestion

ENV PYTHONBUFFERED=1
ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH="$PYTHONPATH:/ingestion_server/"
# TLDEXTRACT fails to cache in /home/supervisord, set its cache to /tmp instead
ENV TLDEXTRACT_CACHE="/tmp/python-tldextract"

WORKDIR /ingestion_server

COPY --from=builder /venv /venv

RUN mkdir /worker_state

EXPOSE 8001 8002
