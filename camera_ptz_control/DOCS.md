# Camera PTZ Control Add-on

This add-on provides a REST API for controlling PTZ cameras and taking pictures.

## Features

- PTZ camera control via REST API
- Take pictures and save them
- Save and restore preset positions
- Home and origin position functions
- Secure password handling
- Swagger UI documentation

## Configuration

### Required configuration:

```yaml
camera_ip: "192.168.1.139"  # Your camera's IP address
password: ""                 # Your camera's password (set securely through the UI)
```

## API Documentation

The API will be available at `http://your-homeassistant:8001` with the following endpoints:

- `/move`: Control PTZ movements
- `/capture`: Take pictures
- `/goto/{location}`: Move to preset locations
- `/savelocation/{name}`: Save current position as preset
- `/origin`: Move to origin position
- `/home`: Move to home position

For detailed API documentation, visit the Swagger UI at `http://your-homeassistant:8001/docs`
