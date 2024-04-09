FROM python:3.10-slim

COPY requirements.txt .

RUN pip install --user -r requirements.txt --no-cache

COPY . .

CMD ["python", "./flat_finder/main.py"]