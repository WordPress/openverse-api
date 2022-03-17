FROM nginx:alpine

RUN apk add openssl \
    && mkdir -p /etc/ssl/private \
    && openssl req  \
      -x509 \
      -out /etc/ssl/certs/localhost.crt \
      -keyout /etc/ssl/private/localhost.key \
      -newkey rsa:2048 \
      -nodes \
      -sha256 \
      -subj '/CN=localhost' -extensions EXT -config <( \
        printf "[dn]\nCN=localhost\n[req]\ndistinguished_name = dn\n[EXT]\nsubjectAltName=DNS:localhost\nkeyUsage=digitalSignature\nextendedKeyUsage=serverAuth" \
      )
