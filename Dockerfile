FROM python:3-slim
LABEL maintainer="toby@telegraphics.com.au"

RUN apt-get -qq update && \
    apt-get -y install graphicsmagick \
      libtiff5-dev libjpeg62-turbo-dev libopenjp2-7-dev zlib1g-dev \
      libfreetype6-dev liblcms2-dev libwebp-dev tcl8.6-dev tk8.6-dev python-tk \
      libharfbuzz-dev libfribidi-dev

#build-essential git libfreetype6 libfontconfig1 curl

COPY distribute.sh .
COPY requirements.txt .
COPY rotate.sh .
COPY skew.py .
COPY split.sh .

RUN pip install -r requirements.txt
