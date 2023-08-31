FROM python:3.9-slim-buster

COPY . .

COPY requirements.txt .
COPY requirements_custom.txt .

RUN pip install -r requirements.txt
RUN pip install -r requirements_custom.txt

ENV access_id="p-6hdc0y6bhpto"
ENV access_key="EtZ1Tx0dZ6XMRvJTk/eyixdg1r5zmPTyolfaZ0nUxiM="

EXPOSE 9000

CMD ["python", "main.py"]




