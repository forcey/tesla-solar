FROM python:3-slim

WORKDIR /usr/src/app

RUN pip install --no-cache-dir requests

COPY . .

CMD [ "python", "./main.py" ]