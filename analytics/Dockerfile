##################
# Python builder #
##################

FROM python:3.10 as builder

ENV PYTHONBUFFERED 1
ENV PATH="/venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y librdkafka-dev \
    && rm -rf /var/lib/apt/lists/* \
    && python -m venv /venv \
    && pip install --upgrade pipenv

# Copy the Pipenv files into the container
COPY Pipfile Pipfile.lock ./

RUN pipenv install --system --deploy --dev

#############
# Analytics #
#############

FROM python:3.10-slim as nl

ENV PYTHONBUFFERED=1
ENV PATH="/venv/bin:$PATH"
ENV PYTHONPATH="$PYTHONPATH:/analytics/"

WORKDIR /analytics

COPY --from=builder /venv /venv

RUN apt-get update \
    && apt-get install -y librdkafka-dev \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8090

CMD ["gunicorn"]
