statelessd
==========

statelessd is a stateless HTTP to AMQP publishing gateway prototype in Python.

The goal is to allow for persistent connections to RabbitMQ for systems and languages that do not facilitate long-running persisted connections like PHP.

It is meant to be run on the same server as any RabbitMQ you intend to publish, or at least it only has the ability to connect to a single RabbitMQ server which, by default is localhost, but can be configured.

You can run any number of statelessd backends, binding to specific port ranges as configured in the HTTPServer -> ports configuration directive. In testing, I run this behind nginx.

It currently does not do any error handling beyond disconnects. While it will log disconnections, it will not prune any temporarily queued messages it is holding until it can connect to RabbitMQ. Therefore it is possible to lose messages if the user specified does not have access to the virtual host specified or if the password is wrong.

## Publishing Messages

Statelessd uses HTTP Basic Auth for obtaining the credentials to connect to RabbitMQ as. The Virtual Host, Exchange and Routing Key come from the URI path and the message body and properties are parsed from x-www-form-urlencoded body values.

### URL Format

    scheme://host[:port]/<VIRTUAL_HOST>/<EXCHANGE>/<ROUTING-KEY>

### Valid POST x-www-form-urlencoded keys

* body
* app_id
* content_encoding
* content_type
* correlation_id
* delivery_mode
* expire
* headers
* message_id
* priority
* reply_to
* timestamp
* type
* user_id

## Stats

The /stats URI will return data collected about the runtime state for a single statelessd backend process. The data collected contains both process information and information detailing publishing numbers. The following example illustrates the types of data available:

    {
        "block": {
            "input": 0,
            "output": 0
        },
        "connections": {
            "messaging:www": {
                "channels": {
                    "closed": 0,
                    "opened": 1
                },
                "connected": true,
                "connections": {
                    "closed": 0,
                    "opened": 1
                },
                "publishes": 11
            }
        },
        "context_switches": 46,
        "cpu_time": {
            "system": 0.056991,
            "user": 0.312952
        },
        "memory_usage": 53752,
        "page_faults": {
            "major": 0,
            "minor": 10366
        },
        "page_size": 4096,
        "port": 8000,
        "signals_received": 0,
        "swap_outs": 0,
        "timestamp": 1362457811
    }

## Examples

### Command Line CURL

    curl --verbose -d body=hi -d "content-type=text/plain" http://guest:guest@localhost:8000/test/test/foo

    * About to connect() to localhost port 8000 (#0)
    *   Trying ::1...
    * Connection refused
    *   Trying 127.0.0.1...
    * connected
    * Connected to localhost (127.0.0.1) port 8000 (#0)
    * Server auth using Basic with user 'guest'
    > POST /test/test/foo HTTP/1.1
    > Authorization: Basic Z3Vlc3Q6Z3Vlc3Q=
    > User-Agent: curl/7.24.0 (x86_64-apple-darwin12.0) libcurl/7.24.0 OpenSSL/0.9.8r zlib/1.2.5
    > Host: localhost:8000
    > Accept: */*
    > Content-Length: 31
    > Content-Type: application/x-www-form-urlencoded
    >
    * upload completely sent off: 31 out of 31 bytes
    < HTTP/1.1 204 No Content
    < Content-Length: 0
    < Content-Type: text/html; charset=UTF-8
    < Server: TornadoServer/2.4.1
    <
    * Connection #0 to host localhost left intact
    * Closing connection #0

### PHP Example using CURL

    <?php
    $virtualHost = '%2f'; // This is the default / virtual host URL quoted
    $username = 'guest';
    $password = 'guest';

    $exchange = 'test';
    $routingKey = 'foo.bar.baz';

    $url = 'http://localhost:8000/' . $virtualHost . '/' . $exchange . '/' . $routingKey;

    $message = array('body' => 'This is a message body published through statelessd',
                     'app_id' => 'PHP Example',
                     'content_type' => 'text/plain',
                     'timestamp' => time(),
                     'type' => 'Example message',
                     'user_id' => $username);

    $curl = curl_init();
    curl_setopt($curl, CURLOPT_URL, $url);
    curl_setopt($curl, CURLOPT_FAILONERROR, true);
    curl_setopt($curl, CURLOPT_FOLLOWLOCATION, true);
    curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($curl, CURLOPT_POST, true);
    curl_setopt($curl, CURLOPT_POSTFIELDS, $message);
    curl_setopt($curl, CURLOPT_USERPWD, $username . ':' . $password);

    $result = curl_exec($curl);
    $headers = curl_getinfo($curl);
    if ($headers['http_code'] === 204)
    {
      echo "Success\n\n";
    } else {
      echo "Failed:\n\n";
      var_dump($headers);
      echo $result;
    }

### Configuration Example

    %YAML 1.2
    ---
    Daemon:
      pidfile: /var/run/statelessd/statelessd.pid
      user: nginx

    Application:
      debug: False
      xsrf_cookies: false
      paths:
        static: /usr/share/statelessd/static
        templates: /usr/share/statelessd/templates
      rabbitmq:
        host: localhost
        port: 5672

    HTTPServer:
      no_keep_alive: false
      ports: [8000, 8001, 8002, 8003, 8004]
      xheaders: false

    Routes:
      - ['/([^/]+)/([^/]+)/([^/]+)', statelessd.Publisher]
      - [/stats, statelessd.Stats]
      - [/, statelessd.Dashboard]

    Logging:
      version: 1
      formatters:
        verbose:
          format: '%(levelname) -10s %(asctime)s %(process)-6d %(processName) -35s %(threadName) -25s %(name) -35s %(funcName) -30s: %(message)s'
          datefmt: '%Y-%m-%d %H:%M:%S'
        syslog:
          format: " %(levelname)s <PID %(process)d:%(processName)s> %(name)s.%(funcName)s(): %(message)s"
      filters: []
      handlers:
        console:
          class: logging.StreamHandler
          formatter: verbose
          debug_only: false
        syslog:
          class: logging.handlers.SysLogHandler
          facility: daemon
          address: /dev/log
          formatter: syslog
      loggers:
        clihelper:
          level: WARNING
          propagate: true
          handlers: [console, syslog]
        pika:
          level: INFO
          propagate: true
          handlers: [console, syslog]
        statelessd:
          level: INFO
          propagate: true
          handlers: [console, syslog]
        tinman:
          level: INFO
          propagate: true
          handlers: [console, syslog]
        tornado:
          level: WARNING
          propagate: true
          handlers: [console, syslog]
      disable_existing_loggers: true
      incremental: false
