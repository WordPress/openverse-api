##################
# Audio waveform #
##################

FROM realies/audiowaveform:latest AS awf

RUN ldd /usr/local/bin/audiowaveform | tr -s '[:blank:]' '\n' | grep '^/' | \
    xargs -I % sh -c 'mkdir -p $(dirname deps%); cp % deps%;'

##################
# Python builder #
##################

FROM python:3.10 AS builder

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

#######
# API #
#######

FROM python:3.10-slim as api

ENV PYTHONBUFFERED=1
ENV PATH="/venv/bin:$PATH"

WORKDIR /openverse_api

ADD catalog/api/utils/fonts/SourceSansPro-Bold.ttf /usr/share/fonts/truetype/SourceSansPro-Bold.ttf

COPY --from=builder /venv /venv

COPY --from=awf /deps /
COPY --from=awf /usr/local/bin/audiowaveform /usr/local/bin

RUN apt-get update \
    && apt-get install -y curl libexempi8 \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /var/log/openverse_api/openverse_api.log

EXPOSE 8000 3000

ENTRYPOINT ["./run.sh"]

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
