FROM ubuntu
MAINTAINER Bhavya bchandra@hsr.ch

RUN apt-get update && apt-get install -y\
	libgeos-dev \ 
	python3-pip

RUN apt-get build-dep -y \
	python-matplotlib \
	python3-lxml
 
WORKDIR /src

ADD requirements.txt /src

RUN pip3 install -r requirements.txt

ADD . /src

RUN crontab crons.conf \
	chmod 777 main.sh

CMD ["cron","-f"]