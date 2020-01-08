FROM python:3.7-alpine

MAINTAINER Isha Bharti "isha.bharti@pubmatic.com"

RUN mkdir -p /app/dfp-prebid-setup/

WORKDIR /app/dfp-prebid-setup/

COPY ./ ./

RUN apk add --update --no-cache g++ gcc libxslt-dev
RUN pip install -r requirements.txt

ENTRYPOINT [ "python3" ]

CMD [ "run.py" ]

