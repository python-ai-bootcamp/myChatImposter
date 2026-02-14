# Stage 1: Build the React production bundle
FROM node:18 AS builder

WORKDIR /app

# Copy package files first for better Docker layer caching
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend source code
COPY frontend/ .

# Build the production bundle (output goes to /app/build)
RUN npm run build


# Stage 2: Serve with nginx
FROM nginx:alpine

# Copy built React app into nginx's default serve directory
COPY --from=builder /app/build /usr/share/nginx/html

# Copy custom nginx configuration
COPY nginx/nginx.conf /etc/nginx/nginx.conf

# Directory for TLS certs (mounted via volume)
RUN mkdir -p /etc/nginx/certs

EXPOSE 80 443
