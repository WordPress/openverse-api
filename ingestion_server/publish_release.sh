# Usage: ./public_release.sh [VERSION]
docker buildx build --platform linux/amd64  -t openverse/ingestion_server:$1 .
# docker build -f Dockerfile-worker -t openverse/indexer_worker:$1 .
docker push openverse/ingestion_server:$1
# docker push openverse/indexer_worker:$1
