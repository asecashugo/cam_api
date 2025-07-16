#!/usr/bin/with-contenv bashio

# Get config values
CAMERA_IP=$(bashio::config 'camera_ip')
CAMERA_PASSWORD=$(bashio::config 'password')

# Create environ.json with the configuration
echo "{\"camera_ip\": \"$CAMERA_IP\", \"pw\": \"$CAMERA_PASSWORD\"}" > /app/environ.json

# Start the FastAPI application
python3 main.py
