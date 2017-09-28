# Overview
HAProxy Automatron is a script that, when executed, will request Let's
Encrypt certificates for all defined domains in haproxy.cfg.

The primary use case is to use with marathon-lb, which is a Mesosphere
HAProxy plugin, that regenerates the haproxy config with topology
changes. This script is designed to be executed by marathon-lb as a
custom reload (--command) command.

This script has no dependencies on marathon, mesos, or any other system
besides `certbot`.

This script can be run on demand, or as a cron job. It is recommend to
as a cronjob to make sure that all certificates are updated, and
on-demand when the topology changes (say, attached to marathon-lb).

## SSL
The default behavior of marathon-lb is to have all information be spoon
feed from marathon. This might work for some, but here we are decoupling
SSL control from marathon. Now, every domain that is configured for
HAProxy (using the HAPROXY_GROUP label) will automatically get an SSL
certificate.

This is better than the default configuration, in that if there was no
SSL certificate for a domain the user will get an invalid certificate
warning in the browser. I don't have to say why this is bad.

# Execution Workflow
1. Marathon-LB is invoked or detects a topology change
2. Marathon-LB completes haproxy.cfg generation and invokes
haproxy_automatron.py
3. haproxy_automatron.py does some preflight checks and then parses
haproxy.cfg and pulls all hostnames. We are assuming DNS is already
configured
4. haproxy_automatron.py try to generate certificates for each hostname
present
5. haproxy_automatron.py will itterate over all certificates in the
`/etc/letsencrypt/live/` directory, and generate a full pem containing
both the chain and private key in `/etc/ssl/haproxy`
6. haproxy_automatron.py will do a configuration check to make sure that
haproxy will come up cleanly when reloaded
7. haproxy_automatron.py will reload haproxy and exit cleanly

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