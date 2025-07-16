ARG BUILD_FROM
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
RUN pip3 install --no-cache-dir -r requirements.txt

# Make scripts executable
RUN chmod a+x /app/run.sh

# Define environment variables
ENV PYTHONUNBUFFERED=1

# Command to run the application
CMD [ "/app/run.sh" ]
