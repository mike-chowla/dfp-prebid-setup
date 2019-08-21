# Use an official Python runtime as a parent image
FROM python:3.7.3-alpine AS base

RUN apk update && \
    apk add git bash && \
    apk add --virtual build-deps gcc libc-dev libxml2-dev libxslt-dev python3-dev && \
    rm -rf /var/cache/apk/*

RUN mkdir -p /code
WORKDIR /code

RUN git clone https://github.com/mike-chowla/dfp-prebid-setup.git
RUN cd dfp-prebid-setup; git checkout openwrap_mods

# Install any needed packages specified in requirements.txt
RUN cd dfp-prebid-setup; pip install --trusted-host pypi.python.org -r requirements.txt

# Make port 80 available to the world outside this container
EXPOSE 80

# Define environment variable
ENV NAME World

# Run app.py when the container launches
CMD ["/bin/bash"]
