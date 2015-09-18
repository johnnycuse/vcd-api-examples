#!/usr/bin/env python                                                                                                    
import base64, getpass, json, pika
from xml.etree.ElementTree import Element, tostring, fromstring

# RabbitMQ Connection Information
rabbit_host       = 'rabbitmqhost'
rabbit_user       = 'vcdextuser'
rabbit_password   = 'vcdextpass'

# Exchange and Queue we will subscribe to
rabbit_exchange   = 'vcdext'
rabbit_routingkey = 'gcp-ticketing'

tickets = {'9aee51e8-654e-49a8-8dab-3fdbf00a21ae' : {'href':'/api/org/9aee51e8-654e-49a8-8dab-3fdbf00a21ae', 
                                                     'name':'Coke', 
                                                     'tickets' : [{'ticket_id':1000, 'user_id': '44fbd6f9-7a76-4bca-b273-3536b181ad09', 'href':'/api/org/9aee51e8-654e-49a8-8dab-3fdbf00a21ae/ticketing/1000', 'ticket_msg': "I am opening a ticket!", 'status' :  "open"}, 
                                                                  {'ticket_id':1001, 'user_id': '44fbd6f9-7a76-4bca-b273-3536b181ad09', 'href':'/api/org/9aee51e8-654e-49a8-8dab-3fdbf00a21ae/ticketing/1001', 'ticket_msg': "My server is slow!", 'status' :  "open"} ]},
           '2ce0365d-4d7d-4c15-a603-9257ea338c99' : {'href':'/api/org/2ce0365d-4d7d-4c15-a603-9257ea338c99',
                                                     'name':'Pepsi', 
                                                     'tickets' : [{'ticket_id':1002, 'user_id': '44fbd6f9-7a76-4bca-b273-3536b181ad09', 'href':'/api/org/9aee51e8-654e-49a8-8dab-3fdbf00a21ae/ticketing/1002', 'ticket_msg': "Can I get some VSAN?", 'status' :  "open"} ]}
}

ticket_id = 2000
pub_channel = None

def _dict_to_xml(tag, d):
    '''
    Turn a simple dict of key/value pairs into XML
    '''
    elem = Element(tag)
    for key, val in d.items():
        child = Element(key)
        child.text = str(val)
        elem.append(child)
    return tostring(elem)

def _xml_to_dict(xml_str):
    '''
    Turn a very set structure of xml to a dictionary.
    '''
    root = fromstring(xml_str)
    ret_dict = {}

    for child in root:
        ret_dict[child.tag] = child.text

    return ret_dict

def _create_ticket(user_id, msg, uri):
    global ticket_id
    ticket_id += 1
    href = "%s/%s" % (uri, str(ticket_id))
    return {'ticket_id':ticket_id, 'href':href, 'user_id':user_id, 'ticket_msg':msg, 'status':"open"} 

def get_org_tickets(org_id):
    ts = [{'ticket_id':t['ticket_id'], 'href':t['href']} for t in tickets[org_id]['tickets']]

    if len(ts) != 0:
        r = ''
        for t in ts:
            r += '\n\t'+_dict_to_xml('ticket', t)
        return '<tickets>%s\n</tickets>' % r
    else:
        return "No tickets found."

def get_ticket(org_id, ticket_id):
    t = [t for t in tickets[org_id]['tickets'] if t['ticket_id'] == ticket_id]

    if len(t) == 1:
        return _dict_to_xml('ticket', t[0])
    else:
        return "No ticket found."

def post_new_ticket(org_id, user_id, msg, uri):
    ticket = _create_ticket(user_id, msg, uri)
    tickets[org_id]['tickets'].append(ticket)
    return _dict_to_xml('ticket', ticket)

def delete_ticket(org_id, ticket_id):
    for i,t in enumerate(tickets[org_id]['tickets']):
        if t['ticket_id'] == ticket_id:
            tickets[org_id]['tickets'].pop(i)
        
    return get_org_tickets(org_id)

def update_ticket(org_id, ticket_id, update_dict):
    ret_str = ''
    for t in tickets[org_id]['tickets']:
        if t['ticket_id'] == ticket_id:
            ret_str = 'PUT XML STRING HERE'
            t.update(update_dict)
            ret_str = _dict_to_xml('ticket', t)
            
    return ret_str

def callback(ch, method, properties, body):
    """
    Function for handeling all messages received on the RabbitMQ Exchange
    """
    print ' [!] Received a message!'
    temp = json.loads(body)
    body = temp[0]
    vcd  = temp[1]
    
    req_uri = body['requestUri'].split('/api/org/')[1].split('/')
    org_id = req_uri[0]

    user_id = vcd['user'].split('user:')[1]
    ticket_id = int(req_uri[-1]) if req_uri[-1].isdigit() else None    
    method = body['method']

    # The response body that we will sent back to the client.
    rsp_body = ''
    status_code = 200

    if method == 'GET':
        if ticket_id:
            rsp_body = get_ticket(org_id, ticket_id) 
        else:
            rsp_body = get_org_tickets(org_id)
    elif method == 'POST' and not ticket_id:
        rsp_body = 'Make sure you provide a message: <ticket>\n\t<ticket_msg>Your mess</ticket_msg>\n</ticket>'
        nt = _xml_to_dict(base64.b64decode(body['body']))
        #Only thing we care about is a msg, make sure it is there
        if nt.get('ticket_msg') != None:
            rsp_body = post_new_ticket(org_id, user_id, nt['ticket_msg'], body['requestUri'])
            status_code = 201
        else:
            # Bad input
            status_code = 400

    elif method == 'PUT' and ticket_id:
        rsp_body = 'To update a ticket provide: <ticket>\n\t<ticket_msg>Your mess</ticket_msg>\n\t<status>open|closed</status>\n</ticket>'
        #Must have ticket_id, and ticket_msg or status
        ut = _xml_to_dict(base64.b64decode(body['body']))
        if ut.get('ticket_msg') != None or ut.get('status') != None:
            #update the ticket
            rsp_body = update_ticket(org_id, ticket_id, ut)
        else:
            # Bad input
            status_code = 400
        
    elif method == 'DELETE' and ticket_id:
        rsp_body = delete_ticket(org_id, ticket_id)
    else:
        #Method not supported.
        status_code = 405
        rsp_body = "ERROR: This method is not supported."

    # Build the response message to return
    rsp_msg ={'id':body['id'],
              'headers':{'Content-Type':body['headers']['Accept'],
                         'Content-Length':len(rsp_body)},
              'statusCode':status_code,
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

    print ' [X] message handeled'

def main():
    print "Starting ticketing..."
    # Connect to RabbitMQ
    connection = pika.BlockingConnection(pika.ConnectionParameters(host=rabbit_host, credentials=pika.PlainCredentials(rabbit_user, rabbit_password)))

    # Create a channel to subscribe to the incoming messages.
    sub_channel = connection.channel()
    sub_channel.exchange_declare(exchange=rabbit_exchange, type='direct', durable=True)
    sub_channel.queue_declare(queue=rabbit_routingkey)
    sub_channel.queue_bind(exchange=rabbit_exchange,
                           queue=rabbit_routingkey)

    # Create a channel for publishing messages back to the client.
    global pub_channel
    pub_channel = connection.channel()
    # Bind to the the queue we will be listening on with a callback function.
    sub_channel.basic_consume(callback,
                              queue=rabbit_routingkey,
                              no_ack=True)

    # Start to continuously monitor the queue for messages.
    sub_channel.start_consuming()
    print ' [*] Waiting for messages on exchange %s. To exit press CTRL+C' % rabbit_exchange

if __name__ == '__main__':
    main()


