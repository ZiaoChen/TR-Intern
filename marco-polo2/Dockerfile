FROM ubuntu:latest
LABEL maintainer="Thibaut Tiberghien <thibaut.tiberghien@thomsonreuters.com>"
LABEL algo-author="Zhan Jiaming <jiaming.zhan@thomsonreuters.com>"
LABEL webapp-author="Chen Ziao <ziao.chen@thomsonreuters.com>"
RUN apt-get update -y
RUN apt-get install -y python3-pip python3-dev build-essential
COPY . /app
WORKDIR /app
RUN pip3 install -r requirements.txt
ENTRYPOINT ["python3"]
CMD ["app.py"]