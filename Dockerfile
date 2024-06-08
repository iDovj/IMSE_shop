# Dockerfile
FROM python:3.10-slim-buster

WORKDIR /app
ADD . /app

COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "run.py"]
    