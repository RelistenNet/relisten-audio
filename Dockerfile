FROM nginx:alpine

RUN mkdir -p /data/nginx/trey

COPY nginx.conf /etc/nginx/nginx.conf
COPY index.html /usr/share/nginx/html/
