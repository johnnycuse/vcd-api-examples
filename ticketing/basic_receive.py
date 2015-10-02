#!/usr/bin/env python                                                                                                    
import base64, getpass, json, pika

# RabbitMQ Connection Information
rabbit_host       = 'rabbitmqhost'
rabbit_user       = 'vcdextuser'
rabbit_password   = 'vcdextpass'

# Exchange and Queue we will subscribe to
rabbit_exchange   = 'vcdext'
rabbit_routingkey = 'gcp-ticketing'


# Connect to RabbitMQ
connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=rabbit_host,
        credentials=pika.PlainCredentials(rabbit_user, rabbit_password)))

# Create a channel to subscribe to the incoming messages.
sub_channel = connection.channel()
sub_channel.exchange_declare(exchange=rabbit_exchange, type='direct', durable=True)
sub_channel.queue_declare(queue=rabbit_routingkey)
sub_channel.queue_bind(exchange=rabbit_exchange, queue=rabbit_routingkey)

print ' [*] Waiting for messages on exchange %s. To exit press CTRL+C' % rabbit_exchange

# Create a channel for publishing messages back to the client.
pub_channel = connection.channel()

def callback(ch, method, properties, body):
  """
  Function for handeling all messages received on the RabbitMQ Exchange
  """
  print ' [!] Received a message!'
  body = json.loads(body)[0]

  # The response body that we will sent back to the client.
  rsp_body = "Got your message!"
  # Build the response message to return
  rsp_msg ={
    'id':body['id'],
    'headers':{'Content-Type':body['headers']['Accept'],
                'Content-Length':len(rsp_body)},
    'statusCode':200,
    'body':base64.b64encode(rsp_body),
    'request':False}

  # vCD sets unique correlation_id in every message sent to extension and the extension must set 
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
                          queue=rabbit_routingkey,
                          no_ack=True)

# Start to continuously monitor the queue for messages.
sub_channel.start_consuming()
