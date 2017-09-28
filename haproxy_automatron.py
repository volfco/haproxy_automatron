#!/usr/bin/env python3

"""
    Marathon-LB Let's Encrypt Middleware
    Copyright (C) 2017 Colum McGaley <colum.mcgaley@fastmail.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

import os
import re
import logging
import sys
import subprocess
import datetime

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
logger.addHandler(ch)

domains = {}

# Preflight checks
if not os.path.exists(os.getenv('CERTBOT_PATH', '/usr/bin/certbot')):
    logger.critical("Certbot is required for this script to work.")
    exit(1)

# Validate that we have the required configuration in the haproxy config
with open(os.getenv('HAPROXY_CFGPATH', '/etc/haproxy/haproxy.cfg'), 'r') as fh:
    if "path_beg -i /.well-known/acme-challenge" not in fh.read():
        logger.critical("Required directive not present in haproxy cfg")
        exit(1)

# Make sure we are working with a valid config
logger.info("Preflight Validation of haproxy configuration")
try:
    proc = subprocess.check_output('/usr/sbin/haproxy -c -V -f {0}'.format(os.getenv('HAPROXY_CFGPATH', '/etc/haproxy/haproxy.cfg')), shell=True, stderr=subprocess.STDOUT)
except subprocess.CalledProcessError as e:
    logger.critical(str(e))
    logger.critical("Failed to validate haproxy config")
    exit(1)
logger.info("...PASSED")

logger.info("HAPROXY_CFGPATH: {0}".format(os.getenv('HAPROXY_CFGPATH', '/etc/haproxy/haproxy.cfg')))
logger.info("HAPROXY_SSLDIR: {0}".format(os.getenv('HAPROXY_SSLDIR', '/etc/ssl/haproxy')))
logger.info("CERTBOT_PATH: {0}".format(os.getenv('CERTBOT_PATH', '/usr/bin/certbot')))

# Find all domains we are dealing with.
# TODO Make this more intelligent by only scanning a block with https config
with open(os.getenv('HAPROXY_CFGPATH', '/etc/haproxy/haproxy.cfg'), 'r') as fh:
    for line in fh.readlines():
        match = re.search(r'acl (.*)hdr\(host\) -i(.*)', line.strip())
        if match is not None:
            data = match.groups()
            logger.info("Found {0}->{1}".format(data[0], data[1]))
            domains[data[1]] = data[0]  # If there are multiple backends for a single domain (say, HTTP & HTTPS), that sucks for them


# Renew certs so we can do the processing at once
logger.info("Renewing all certs")
proc = subprocess.check_output('certbot renew', shell=True, stderr=subprocess.STDOUT)
output = proc.decode('utf-8')
for line in output.split('\n'):
    logger.debug(line)

# Loop over each domain and process it
if domains.__len__() > 0:
    logger.info("Processing {0} domains".format(domains.__len__()))
    for domain in domains:
        args = ['certbot', 'certonly', '--noninteractive', '--agree-tos', '--standalone', '--preferred-challenges', 'http', '--http-01-port', '6709', '-d', domain, '--email', os.getenv('CERTBOT_EMAIL')]

        logger.info("Executing: {0}".format(' '.join(args)))
        proc = subprocess.check_output(' '.join(args), shell=True, stderr=subprocess.STDOUT)
        output = proc.decode('utf-8')
        for line in output.split('\n'):
            logger.debug(line)
else:
    logging.warning("No Domains found. Nothing to do")
    exit(0)

# Cleanup PEM files from previous runs.
for pem in os.listdir(os.getenv('HAPROXY_SSLDIR', '/etc/ssl/haproxy')):
    match = re.search(r'haproxy_le-full_(.*).pem', pem)
    if match is not None:
        domain = match.groups()[0].split('_')[-1]
        path = "/etc/letsencrypt/live/{0}/".format(domain)
        if not os.path.exists(path):
            logger.warning('Domain {0} does not seem to exist in LE\'s working directory.'.format(domain))
        else:
            logger.info("Deleting {0}".format("/etc/ssl/haproxy/{0}".format(pem)))
            os.remove("/etc/ssl/haproxy/{0}".format(pem))
    else:
        logger.debug("Ignoring {0}. Not ours".format(pem))

# Generate new PEM files for all live certificates
for ditm in os.listdir('/etc/letsencrypt/live/'):
    path = "/etc/letsencrypt/live/{0}/".format(ditm)
    if os.path.isdir(path):
        logger.debug("Found live key {0}".format(ditm))

        pkey = open("{0}privkey.pem".format(path), 'r').read()
        fcrt = open("{0}fullchain.pem".format(path), 'r').read()
        ctime = datetime.datetime.now()
        outfile = "{0}/haproxy_le-full_{1}_{2}_{3}_{4}.pem".format(os.getenv('HAPROXY_SSLDIR', '/etc/ssl/haproxy'), ctime.year, ctime.month, ctime.day, ditm)
        wfh = open(outfile, 'w+')
        wfh.write(pkey + fcrt)
        wfh.close()

        logger.info("Wrote haproxy PEM {0}".format(outfile))

# Final Sanity check
logger.info("Validating haproxy configuration...")
try:
    proc = subprocess.check_output('/usr/sbin/haproxy -c -V -f {0}'.format(os.getenv('HAPROXY_CFGPATH', '/etc/haproxy/haproxy.cfg')), shell=True, stderr=subprocess.STDOUT)
except subprocess.CalledProcessError as e:
    logger.critical(str(e))
    logger.critical("Failed to validate haproxy config")
    exit(1)

output = proc.decode('utf-8')
for line in output.split('\n'):
    logger.debug(line)

logger.info('Reloading haproxy')
subprocess.call('systemctl reload haproxy', shell=True, stderr=subprocess.STDOUT)

exit(0)