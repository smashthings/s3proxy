FROM smasherofallthings/flask-waitress

RUN mkdir -p /public/templates
COPY s3_proxy.py /public
COPY templates /public/templates

ENV PYTHONUNBUFFERED=TRUE

CMD ["/usr/bin/python3", "/public/s3_proxy.py"]
