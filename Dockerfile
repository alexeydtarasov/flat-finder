FROM python:3.10-slim

ENV PROD=1
ENV BASE_PATH="/app"
COPY requirements.txt .

RUN pip install --user -r requirements.txt --no-cache

COPY . app