FROM ubuntu
MAINTAINER Bhavya bchandra@hsr.ch

RUN apt-get update && apt-get install -y\
	libgeos-dev \ 
	python3-pip

RUN apt-get build-dep -y \
	python-matplotlib \
	python3-lxml
 
WORKDIR /src

ADD . /src

RUN pip3 install -r requirements.txt

CMD ["./main.sh"]