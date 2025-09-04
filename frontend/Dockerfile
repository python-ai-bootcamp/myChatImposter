# Use a Node.js LTS version as a base image
FROM node:20-slim

# Set the working directory in the container
WORKDIR /app

# Copy package.json and package-lock.json (if it exists)
# The `*` is to handle the case where package-lock.json may not exist
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application source code
COPY . .

# Create React App runs on port 3000 by default
EXPOSE 3000

# Set the command to start the development server
# Using 0.0.0.0 is important to allow the server to be accessible from outside the container
CMD ["npm", "start"]
