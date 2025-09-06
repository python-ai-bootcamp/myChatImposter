# Use an official Node.js runtime as a parent image
FROM node:18

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json
COPY chat_providers/whatsapp_baileys_server/package.json ./
# If you have a package-lock.json, copy it as well
# COPY chat_providers/whatsapp_baileys_server/package-lock.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application code
COPY chat_providers/whatsapp_baileys_server/ .

# The server will be started with arguments from the docker-compose file, so no CMD is needed here.
# However, we can provide a default command for running it standalone.
# The port will be passed as an argument.
CMD ["node", "server.js"]
