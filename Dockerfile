FROM nginx:alpine

# the volume mount should handle this
# RUN mkdir -p /data/nginx/trey

COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /data/nginx/
