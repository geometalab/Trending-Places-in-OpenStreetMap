FROM ubuntu:14.04
MAINTAINER Geometalab geometalab@hsr.ch

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y -q --no-install-recommends \
	libgeos-dev libxslt1.1 libfreetype6 \
  python3-pip python3-matplotlib python3-lxml \
  cron \
  && apt-mark manual $(apt-mark showauto)

WORKDIR /src
ADD . /src

RUN apt-mark showmanual | sort >/tmp/maninst \
  && apt-get build-dep -y -q --no-install-recommends -s \
     python3-matplotlib python3-lxml | sed -r -n -e 's|^Inst\s+([^ ]+).*$|\1|p' | sort >/tmp/bdeps \
  && apt-get install -y -q --no-install-recommends $(cat /tmp/bdeps) \
  && export MAKEFLAGS="-j $(nproc)" && pip3 install -r requirements.txt \
  && apt-mark auto $(join -v 2 /tmp/maninst /tmp/bdeps) | grep -v "was already set" \
  && apt-get autoremove -y && apt-get purge -y && apt-get clean -y \
  && rm -f /tmp/*

RUN chmod 0755 main.sh run_cron.sh

ENV PYTHONUNBUFFERED=non-empty-string
ENV PYTHONIOENCODING=utf-8
CMD ["./run_cron.sh"]