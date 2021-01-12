FROM python:3.7.3

WORKDIR /app

COPY *.py /app/

COPY requirements.txt /app/requirements.txt

RUN bash -c 'https_proxy=http://10.227.9.241:8888/ http_proxy=http://10.227.9.241:8888/ pip3 install --requirement requirements.txt'

EXPOSE 4777

CMD ["python3", "/app/app.py"]
