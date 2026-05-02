# Use an official Python runtime as a parent image
FROM python:3.14-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install gosu and dos2unix for entrypoint permissions handling
RUN apt-get update && apt-get install -y gosu dos2unix && rm -rf /var/lib/apt/lists/*

# Create a non-root group and user (IDs will be dynamically modified by entrypoint)
RUN groupadd -g 1500 media_group && useradd -m -u 1500 -g media_group appuser

# Copy the rest of the application code
COPY . .

# Expose the port the app runs on
EXPOSE 8000

# Copy and convert entrypoint script for Windows host compat
COPY scripts/backend-entrypoint.sh /usr/local/bin/entrypoint.sh
RUN dos2unix /usr/local/bin/entrypoint.sh && chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Keep container primary user as root so the entrypoint can dynamically adjust permissions before dropping to appuser
USER root

# Command to run the application (will be passed to entrypoint.sh)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
