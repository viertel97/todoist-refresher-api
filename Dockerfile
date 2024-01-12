FROM python:3.9-slim-buster
ARG PAT
RUN apt-get update &&  apt-get install -y git

COPY . .

COPY requirements.txt .

RUN pip install -r requirements.txt --extra-index-url https://pkgs.dev.azure.com/viertel/Quarter-Lib/_packaging/Quarter-Lib/pypi/simple/

RUN echo "    IdentityFile /ssh/id_rsa" >> /etc/ssh/ssh_config

ENV IS_CONTAINER=True

EXPOSE 9000

CMD ["python", "main.py"]




