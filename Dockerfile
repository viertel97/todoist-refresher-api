ARG PYTHON_BASE=3.11-slim-buster
ARG PAT

FROM python:$PYTHON_BASE AS builder
ARG PAT

RUN pip install -U pdm

ENV PDM_CHECK_UPDATE=false

COPY pyproject.toml pdm.lock README.md /project/
COPY src/ /project/src

WORKDIR /project
RUN pdm install --check --prod --no-editable

FROM python:$PYTHON_BASE
RUN apt-get update &&  apt-get install -y git


COPY --from=builder /project/.venv/ /project/.venv
ENV PATH="/project/.venv/bin:$PATH"
ENV PYTHONPATH="/project"

EXPOSE 9100

COPY src /project/src

CMD ["python", "/project/src/main.py"]