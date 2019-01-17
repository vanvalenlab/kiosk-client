FROM ubuntu:18.04

RUN apt-get update && apt-get install -y \
    firefox \
    python3 \
    python3-pip \
    wget

RUN ln -s /usr/bin/python3 /usr/bin/python && ln -s /usr/bin/pip3 /usr/bin/pip

RUN pip install numpy pillow selenium

COPY benchmarking.sh benchmarking_images_generation.py file_upload.py /

CMD ["sleep","1000000"]
