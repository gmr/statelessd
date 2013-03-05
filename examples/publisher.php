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
