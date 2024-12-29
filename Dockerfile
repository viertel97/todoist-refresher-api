ARG PYTHON_BASE=3.11-slim-buster
ARG PAT
# build stage
FROM python:$PYTHON_BASE AS builder
ARG PAT

# install PDM
RUN pip install -U pdm
# disable update check
ENV PDM_CHECK_UPDATE=false
# copy files
COPY pyproject.toml pdm.lock README.md /project/

# install dependencies and project into the local packages directory
WORKDIR /project
RUN pdm config --local pypi.url "https://Quarter-Lib-Old:${PAT}@pkgs.dev.azure.com/viertel/Quarter-Lib-Old/_packaging/Quarter-Lib-Old/pypi/simple/"
RUN pdm install --check --prod --no-editable

# run stage
FROM python:$PYTHON_BASE
RUN apt-get update &&  apt-get install -y git

# retrieve packages from build stage
COPY --from=builder /project/.venv/ /project/.venv
ENV PATH="/project/.venv/bin:$PATH"
# set command/entrypoint, adapt to fit your needs

EXPOSE 9100
RUN echo "    IdentityFile /ssh/id_rsa" >> /etc/ssh/ssh_config
RUN echo "    StrictHostKeyChecking no" >> /etc/ssh/ssh_config
CMD ["python", "main.py"]