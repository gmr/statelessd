"""
publisher.py

Requires the "requests" library

"""
import requests
import time
import urllib

virtual_host = '/'
username = 'guest'
password = 'guest'

exchange = 'test'
routing_key = 'foo.bar.baz'

data = {'body': 'This is a test message published through statelessd',
        'app_id': 'Python example',
        'content_type': 'text/plain',
        'timestamp': int(time.time()),
        'type': 'Test Message',
        'user_id': username}


# urllib.quote needs the safe value of / removed
url = 'http://localhost:8000/%s/%s/%s' % (urllib.quote(virtual_host, ''),
                                          exchange,
                                          routing_key)

response = requests.post(url, auth=(username, password), data=data)
if response.status_code == 204:
    print 'Success!'
    print
else:
    print 'Error: %s' % response.status_code
    print response.content
    print
