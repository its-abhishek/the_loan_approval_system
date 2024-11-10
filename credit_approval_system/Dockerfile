FROM python:3.10-slim
WORKDIR /code
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
# Create a non-root user and switch to it
RUN adduser --disabled-password --gecos '' myuser && chown -R myuser /code
USER myuser