set dotenv-load := false

DOCKER_FILE := "-f docker-compose.yml"
SERVICE_NAME := ""


install:
    pipenv install --dev
    pipenv run pre-commit install


init: up
    ./load_sample_data.sh


healthcheck:
    curl localhost:8000/v1/images?q=honey


test: up
    docker-compose exec web bash ./test/run_test.sh


up:
    docker-compose {{ DOCKER_FILE }} up -d


down args="":
    docker-compose {{ DOCKER_FILE }} down {{ args }}


logsweb:
    docker-compose {{ DOCKER_FILE }} logs -f web


logsall:
    docker-compose {{ DOCKER_FILE }} logs -f
