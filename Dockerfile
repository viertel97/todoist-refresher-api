FROM python:3.9-slim-buster
ARG PAT
RUN apt-get update &&  apt-get install -y git

COPY . .

COPY requirements.txt .

RUN pip install -r requirements.txt --extra-index-url https://pkgs.dev.azure.com/viertel/Quarter-Lib/_packaging/Quarter-Lib/pypi/simple/


ENV IS_CONTAINER=True

EXPOSE 9000
RUN echo "    IdentityFile /root/ssh/id_rsa" >> /etc/ssh/ssh_config
RUN echo "    StrictHostKeyChecking no" >> /etc/ssh/ssh_config
CMD ["python", "main.py"]




