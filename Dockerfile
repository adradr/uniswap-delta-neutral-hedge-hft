# Dockerfile
# Using official Python 3.10 runtime base image
FROM python:3.10

# Set the working directory in the container to /app
WORKDIR /docker-app

# Add the current directory contents into the container at /app
ADD app_cex.py app_dex.py setup.py /docker-app/
ADD uniswap_hft /docker-app/uniswap_hft

# Install the local package
RUN pip install .

# Set environment varibles
ENV PYTHONUNBUFFERED 1

# Add labels
LABEL version="1.0"
LABEL maintainer="adradr <adrian.lenard@me.com>"
LABEL description="Docker image for Uniswap HFT"
LABEL repository="https://github.com/adradr/uniswap-delta-neutral-hedge-hft"
