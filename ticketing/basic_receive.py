#!/usr/bin/env python
import base64, json, pika

# RabbitMQ Connection Information
RABBIT_HOST = 'rabbitmqhost'
RABBIT_USER = 'vcdextuser'
RABBIT_PASSWORD = 'vcdextpass'

# Exchange and Queue we will subscribe to
RABBIT_EXCHANGE = 'vcdext'
RABBIT_ROUTINGKEY = 'gcp-ticketing'


# Connect to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(\
  host=RABBIT_HOST, credentials=pika.PlainCredentials(RABBIT_USER, RABBIT_PASSWORD)))

# Create a channel to subscribe to the incoming messages.
sub_channel = connection.channel()
sub_channel.exchange_declare(exchange=RABBIT_EXCHANGE, exchange_type='direct', durable=True)
sub_channel.queue_declare(queue=RABBIT_ROUTINGKEY)
sub_channel.queue_bind(exchange=RABBIT_EXCHANGE, queue=RABBIT_ROUTINGKEY)

print ' [*] Waiting for messages on exchange %s. To exit press CTRL+C' % RABBIT_EXCHANGE

# Create a channel for publishing messages back to the client.
pub_channel = connection.channel()

def callback(ch, method, properties, body):
    """
    Function for handleing all messages received on the RabbitMQ Exchange
    """
    print ' [!] Received a message!'
    body = json.loads(body)[0]

    # The response body that we will sent back to the client.
    rsp_body = "Got your message!"
    # Build the response message to return
    rsp_msg = {'id':body['id'],
               'headers':{'Content-Type':body['headers']['Accept'],
                          'Content-Length':len(rsp_body)},
               'statusCode':200,
               'body':base64.b64encode(rsp_body),
               'request':False}

    # vCD sets unique correlation_id in every message sent to extension and the extension must set.
    # the same value in the corresponding response.
    rsp_properties = pika.BasicProperties(correlation_id=properties.correlation_id)

    print "\t Sending response..."
    # We send our response to the Exchange and queue that were specified in the received properties.
    pub_channel.basic_publish(properties.headers['replyToExchange'],
                              properties.reply_to,
                              json.dumps(rsp_msg),
                              rsp_properties)

    print ' [X] message handled.'

# Bind to the the queue we will be listening on with a callback function.
sub_channel.basic_consume(callback,
                          queue=RABBIT_ROUTINGKEY,
                          no_ack=True)

# Start to continuously monitor the queue for messages.
sub_channel.start_consuming()
