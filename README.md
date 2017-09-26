# Overview
HAProxy Automatron is a script that, when executed, will request Let's
Encrypt certificates for all defined domains in haproxy.cfg.

The primary use case is to use with marathon-lb, which is a Mesosphere
HAProxy plugin, that regenerates the haproxy with topology changes. This
script is designed to be executed by marathon-lb as a custom reload
command.

This script has no dependencies on marathon, mesos, or any other system
besides `certbot`. It can be run independently.

# Required Configuration

## HAproxy
This script requires a custom ACL to proxy incoming challenges in the
http (port 80) frontend. The script will look for this directive before
it executes.
```
frontend http-frontend
    mode    http
    bind    :80

    acl is_certbot path_beg -i /.well-known/acme-challenge
    use_backend certbot if is_certbot
```
You also need to add a custom backend to handle Let's Encrypt
challenges.
```
backend certbot
    log global
    mode http
    server certbot 127.0.0.1:6907
```
# Usage
## Independently
```
./haproxy_automatron.py
```
## Marathon-LB
```
python3 marathon_lb.py --command 'haproxy_automatron.py'
```

# Environmental Variables
## CERTBOT_EMAIL
E-Mail Address for certbot

## CERTBOT_PATH
Absolute path to the certbot executable. Defaults to `/usr/bin/certbot`

This will be depreciated in the
future to directly use the certbot python package.

## HAPROXY_CFGPATH
Absolute path to the haproxy config that will be modified. Defaults to
`/etc/haproxy/haproxy.cfg`

## HAPROXY_SSLDIR
Directory HAProxy will look for SSL Certificate files. Defaults to
`/etc/ssl/haproxy`