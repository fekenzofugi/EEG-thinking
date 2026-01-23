FROM python:3.12.3-slim

# Set the working directory
WORKDIR /geohuman_app

# Install gcc
RUN apt-get update && apt-get install -y gcc libgl1-mesa-glx curl libglib2.0-0

COPY requirements.txt /geohuman_app

RUN pip install --no-cache-dir -r requirements.txt

COPY service_entrypoint.sh /geohuman_app/

# Copy the rest of the application code
COPY . /geohuman_app/

# Set the environment variables
RUN chmod +x service_entrypoint.sh

# Expose the port the app runs on
EXPOSE 5000

ENTRYPOINT [ "./service_entrypoint.sh" ]