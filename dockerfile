FROM ubuntu:latest

RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
RUN apt-get install -y python3-venv

WORKDIR /home/mqubel

RUN pip3 install flask pony psycopg2 requests flask-cors

COPY webserver.py ./

ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV FLASK_APP webserver.py
ENV FLASK_ENV development

EXPOSE 5000
CMD python3 -m flask run --host=0.0.0.0
