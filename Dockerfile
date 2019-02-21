FROM ubuntu:18.04

RUN apt-get update && apt-get install -y \
    chromium-browser \
    chromium-chromedriver \
    python3 \
    python3-pip \
    wget


# configureing tzdata non-intercatively, to enable the installation of expect,
# which contains the unbuffer command
ENV DEBIAN_FRONTEND noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN true
RUN echo "tzdata tzdata/Areas select America" > /tmp/preseed.txt; \
    echo "tzdata tzdata/Zones/America select Los_Angeles" >> /tmp/preseed.txt; \
    debconf-set-selections /tmp/preseed.txt && \
    #rm /etc/timezone && \
    #rm /etc/localtime && \
    apt-get update && \
    apt-get install -y tzdata

RUN apt-get install -y expect

RUN ln -s /usr/bin/python3 /usr/bin/python && ln -s /usr/bin/pip3 /usr/bin/pip

RUN pip install \
    numpy \
    pillow \
    redis \
    selenium

COPY benchmarking.sh \
     benchmarking_images_generation.py \
     file_upload.py \
     redis_polling.py \
     /

CMD /benchmarking.sh
