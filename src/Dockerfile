# For more information, please refer to https://aka.ms/vscode-docker-python
FROM python:latest

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

WORKDIR /usr/src/redis-ha
COPY . /usr/src/redis-ha/

RUN pip install -r requirements.txt

CMD ["python", "consumer.py"]
