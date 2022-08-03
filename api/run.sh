#!/bin/bash

set -e

while [ "$(curl -s -o /dev/null -w '%{http_code}' "http://${ELASTICSEARCH_URL:-es}:${ELASTICSEARCH_PORT:-9200}/_cluster/health")" != "200" ]; do
  echo "Waiting for Elasticsearch connection..." && sleep 5;
done
echo "Elasticsearch connection established!"

exec "$@"
