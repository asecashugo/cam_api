ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:3.16
FROM $BUILD_FROM

# Install required packages
RUN \
    apk add --no-cache \
        python3 \
        py3-pip \
        opencv \
        py3-opencv \
        gcc \
        python3-dev \
        musl-dev \
        linux-headers \
        cmake \
        make \
        g++

# Copy your application files
WORKDIR /app
COPY . .

# Create and set permissions for pictures directory
RUN mkdir -p /config/pictures/cam_api && \
    chmod -R 777 /config/pictures/cam_api

# Ensure WSDL directory has proper permissions
RUN chmod -R 755 /app/wsdl

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir --ignore-installed packaging==25.0 && \
    pip3 install --no-cache-dir --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir -r requirements.txt

# Make scripts executable
RUN chmod a+x /app/run.sh

# Define environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD [ "/app/run.sh" ]
