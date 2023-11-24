FROM python:3.9-slim-buster

RUN apt-get update && apt-get upgrade -y && apt-get install -y git

COPY . .

COPY requirements.txt .
COPY requirements_custom.txt .

RUN pip install -r requirements.txt
RUN pip install -r requirements_custom.txt

ENV IS_CONTAINER=True

EXPOSE 9000

CMD ["python", "main.py"]




