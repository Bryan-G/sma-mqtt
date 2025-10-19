# Use a minimal Python base image
FROM python:3.9-slim

# Set the working directory inside the container
WORKDIR /app

COPY sma-mqtt.py /app/sma-mqtt.py
COPY requirements.txt /app/requirements.txt

# Install the required dependencies
RUN pip install -r requirements.txt

# Set the entrypoint for the container to execute the Python script
ENTRYPOINT ["python", "sma-mqtt.py"]
