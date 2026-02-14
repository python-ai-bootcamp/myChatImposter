# Stage 1: Build the React production bundle
FROM node:18 AS builder

WORKDIR /app

# Copy package files first for better Docker layer caching
COPY frontend/package.json frontend/package-lock.json* ./

# Install dependencies
RUN npm install

# Copy the rest of the frontend source code
COPY frontend/ .

# Build the production bundle
RUN npm run build

# Stage 2: The final image just holds the build output.
# nginx will access it via a shared volume.
FROM alpine:3.19

# Copy build output from builder stage
COPY --from=builder /app/build /usr/share/frontend/build

# This container doesn't need to run anything — it just holds the files.
# docker-compose will use volumes_from or a named volume to share them.
CMD ["echo", "Frontend build complete. Static files at /usr/share/frontend/build"]
