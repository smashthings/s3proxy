ARG FE_BUILD
ARG BASEIMAGE

FROM $FE_BUILD AS frontend
RUN mkdir -p /app/dist /app/templates /app/static
WORKDIR /app
COPY templates/ /app/templates/
COPY static/ /app/static/
COPY build.js package.json package-lock.json tailwind.config.js /app
RUN npm install && npm run prod

FROM $BASEIMAGE
RUN mkdir -p /app/dist
WORKDIR /app
COPY s3_proxy.py requirements.txt /app
COPY --from=frontend /app/dist/index.html /app/dist/settings.html /app/dist/

RUN python3 -m pip install -r requirements.txt --break-system-packages && chmod a+x /app/s3_proxy.py

ENV PYTHONUNBUFFERED=TRUE
EXPOSE 3000

CMD ["/app/s3_proxy.py"]
