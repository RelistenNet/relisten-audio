FROM nginx:alpine

# the volume mount should handle this
# RUN mkdir -p /data/nginx/trey

COPY nginx.conf /etc/nginx/nginx.conf
COPY cors.conf /etc/nginx/cors.conf
COPY proxy.conf /etc/nginx/proxy.conf

COPY index.html /data/nginx/
