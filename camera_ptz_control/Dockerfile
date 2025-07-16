ARG BUILD_FROM=ghcr.io/home-assistant/aarch64-base:3.16
FROM $BUILD_FROM

# Install required packages
RUN \
    apk add --no-cache \
        python3 \
        py3-pip \
        opencv \
        gcc \
        python3-dev \
        musl-dev \
        linux-headers

# Copy your application files
WORKDIR /app
COPY . .

# Install Python dependencies
RUN pip3 install --no-cache-dir --upgrade pip setuptools wheel && \
    pip3 install --no-cache-dir --ignore-installed "packaging>=24.0" && \
    pip3 install --no-cache-dir opencv-python-headless==4.5.5.64 && \
    pip3 install --no-cache-dir -r requirements.txt

# Make scripts executable
RUN chmod a+x /app/run.sh

# Define environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD [ "/app/run.sh" ]
