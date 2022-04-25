FROM smasherofallthings/flask-waitress

RUN mkdir /public
COPY s3_proxy.py /public
COPY templates /public

CMD ["python3", "/public/s3_proxy.py"]
