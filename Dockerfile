FROM python:3-slim

WORKDIR /usr/src/app

RUN pip install --no-cache-dir requests

COPY . .

# https://stackoverflow.com/questions/29663459/python-app-does-not-print-anything-when-running-detached-in-docker
CMD [ "python", "-u", "./main.py" ]