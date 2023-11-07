import argparse
import json
from more_utils.messaging import RabbitMQFactory
import yaml

class ServerMessageHandler:
    def __init(self):
        self.message = None

    def handler(self, message):
        self.message = json.loads(message)


parser = argparse.ArgumentParser(description="Messaging Client")
parser.add_argument("--config", help="Path to run configuration yaml", required=True)
parser.add_argument("--credentials", required=True)
parser.add_argument("--broker_user", help="Defaults to credentials file")
parser.add_argument("--broker_password", help="Defaults to credentials file")
args = parser.parse_args()

rabbitmq_context = RabbitMQFactory.create_context(
    args, args.broker_user, args.broker_password
)

with rabbitmq_context.client() as client:
    
    publisher = client.get_publisher()
    with open(args.config) as fp:
        run_configs = yaml.safe_load(fp)
    publisher.publish(json.dumps(run_configs))

    receiver = client.get_consumer()

    print("Waiting for response...")
    while True:
        message = receiver.receive(handler=ServerMessageHandler().handler, max_messages=1, timeout=None)
        message = message.decode("UTF-8")
        message = json.loads(message)
        print("Message Received: ", message)

        if message["status"] in ["COMPLETED", "ERROR"]:
            break