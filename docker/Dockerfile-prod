FROM python:alpine

RUN apk update && apk upgrade

COPY ./requirements.txt /requirements.txt
RUN pip install -r /requirements.txt gunicorn
COPY ./publications /code/publications
RUN mkdir /code/site
WORKDIR /code/publications
ENV PYTHONPATH /code

# XXX Change for tornado!
#ENV GUNICORN_CMD_ARGS "--bind=0.0.0.0:8000 --workers=1 --thread=4 --worker-class=gthread --forwarded-allow-ips='*' --access-logfile -"
#CMD ["gunicorn", "app:app"]

VOLUME ["/code/site"]
