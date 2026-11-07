FROM nginx:alpine

# Pick up Alpine security fixes the upstream nginx image hasn't been rebuilt with yet
RUN apk upgrade --no-cache

# the volume mount should handle this
# RUN mkdir -p /data/nginx/trey

COPY nginx.conf /etc/nginx/nginx.conf
COPY cors.conf /etc/nginx/cors.conf
COPY proxy.conf /etc/nginx/proxy.conf
COPY store.conf /etc/nginx/store.conf
COPY store_policy.js /etc/nginx/store_policy.js

COPY index.html /data/nginx/
