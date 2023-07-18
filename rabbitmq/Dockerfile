FROM rabbitmq:3-management-alpine

RUN sed -i 's/origin text/new text/g' /etc/sysctl.conf

COPY rabbitmq.conf /etc/rabbitmq/rabbitmq.conf
COPY definitions.json /etc/rabbitmq/definitions.json
