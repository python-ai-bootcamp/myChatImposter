# Use an official Node.js runtime as a parent image
FROM node:20

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json
COPY chat_providers/whatsapp_baileys_server/package.json ./
# If you have a package-lock.json, copy it as well
# COPY chat_providers/whatsapp_baileys_server/package-lock.json ./

# Install dependencies
RUN npm install

# Install gosu and dos2unix for entrypoint permissions handling
RUN apt-get update && apt-get install -y gosu dos2unix && rm -rf /var/lib/apt/lists/*

# Create a non-root group and user (IDs will be dynamically modified by entrypoint)
RUN groupadd -g 1500 media_group && useradd -m -u 1500 -g media_group appuser

# Copy the rest of the application code
COPY chat_providers/whatsapp_baileys_server/ .

# The server will be started with arguments from the docker-compose file
# Copy and convert entrypoint script for Windows host compat
COPY scripts/whatsapp-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN dos2unix /usr/local/bin/entrypoint.sh && chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Keep container primary user as root so the entrypoint can dynamically adjust permissions before dropping to appuser
USER root

# The port will be passed as an argument.
CMD ["node", "server.js"]
