FROM nginx:alpine

# Copy custom configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Directory for certs (mounted via volume, but ensuring it exists)
RUN mkdir -p /etc/nginx/certs

EXPOSE 80 443
