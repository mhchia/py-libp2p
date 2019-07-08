import asyncio
import sys
import urllib.request

from Crypto.PublicKey import RSA
import click
import multiaddr

from libp2p import new_node
from libp2p.peer.id import id_from_public_key
from libp2p.peer.peerinfo import info_from_p2p_addr
from libp2p.protocol.identify import id as id_protocol


PROTOCOL_ID = '/chat/1.0.0'


async def read_data(stream):
    while True:
        read_string = await stream.read()
        if read_string is not None:
            read_string = read_string.decode()
            if read_string != "\n":
                # Green console colour: 	\x1b[32m
                # Reset console colour: 	\x1b[0m
                print("\x1b[32m %s\x1b[0m " % read_string, end="")


async def write_data(stream):
    loop = asyncio.get_event_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        await stream.write(line.encode())


async def run(port, destination):
    external_ip = urllib.request.urlopen(
        'https://v4.ident.me/').read().decode('utf8')
    external_ip = "127.0.0.1"
    transport_opt = "/ip4/%s/tcp/%s" % (external_ip, port)

    # FIXME: fixed the key to make testing easier
    rsa_key_pem = b'-----BEGIN RSA PRIVATE KEY-----\nMIIEpAIBAAKCAQEA4rv8Ddzc71Y8v2+MpR4ThHDarxq9ZnQ1aQHjQZNqwgkgfxzw\nObVrjUiO4K9ViCqghC3TjIuXWue/ZDzidd+kgpPYfehLw8ByIlnBZSIIERYdpEsn\nMRiLuKH0HBS41gM1IgeVLixnnUFSVNDmBdoPedLKFHkurqM/8N9CCJBfVo3KvyLW\nAp56KpEJpsJfTpEUphQd9ZIQYhu3cPKCxG5Qt7A+vrDqMbKf0/FxD/DHq6ocAqBZ\nxGOgOpciEKfJjIpEjyL0EhaGo95q95mR/E9z5t/7mCoHCLAzysU2Odj5RnRkGP+H\nURbpNtplUhsQp+iSKS4XglFyVLGydvqx8YA10wIDAQABAoIBAGdteEe8mf4FmTV8\nhaxmoWGXd3JMINzlIt4RUeD+hcMYlb3WbhDtHLA4ypBc+wff5hQVsXxZywPZVnm7\nulQp3ioAlk+tES6tEYNw7SMcmJBuxbvF2o1vVIE3Q5sxqrVZhjnNOrRy5hsaipuN\nJXjC5a9dQ/h95Rkd+BOBTGaKsSrSLGwK9X+yPpIOCmVG0v8yM7UTu/sWN01gA+1y\nE1R88lHY0S6AiTmm7LZZ1scd7vthkpfO/WGsLh6sKc5oGf/WUo037RthLw5mChS/\n7gFCNAwMMf+uCqBvO756d+B54y9eokX6VQErMj04OvdFVQmVnkbVDu1ETRJCDisC\nuHH+ai0CgYEA5D9IGs9idkHMNT7YtNchXNaNzaf5Jlv0wsBUXTtsG2e44eOmaAMd\nWZjldoNrYE2fKIyD46975JMW2ZbmETDxe6kwR2Kiav5Sb7b9hAYqevL6v/H1IwkE\nx/o4p3AwpY/gR8pjGYMQU8A/dAyYuhw53cqOkZM9QhwCOsa1r6bI1T8CgYEA/k2c\ncCwztgQj2wSrCW+lgQnMJ4J+m+xFhhJCWfieVnZOgE8Exga6luf3cFkyLFw1tQUS\njDqYbm2+k3VVqqyk9mgkd2/ftX3hpKna44rSDpo+4V5wOw+CJSqv9qEfHSI5LEAv\nfRB4SDG/xns8c5NRx0B3EHYvvMkENHZ/yFfWFm0CgYAGHZv0+/GLcZ/jHVf5IHqI\nXkdWZ1XJrVUVksmv5dOzuEe/5bWju9GhgPNFBahu4CWPlJREGYOcUESgd+aaN1GB\nGrtsbjwj2cSjsaeBThj9Sl1lnzoOQkOaiB3UfrEO/pfn1IhrOpPJarFIjr3Y3sC+\nLJs9U1Ck4NM+d+yOVE21SQKBgQDxa6rNTxlUff+wKHFbhvN/WlbHV3ps+lRSYLk/\nAukGuk/yPZIRkUfIhbWBohwgwvV1wbgHCoW1qFgZU3YdjsMY7mtYPAwMF9KEaYBV\nLnAWztZNTEONvj5WnHzqzbFlDh1q5hBvUZhvKVOf0VTlgAFOAORH63uMZOWqDKlp\nAAJNzQKBgQC28TBoscdv8cnszV5SBwnc1XE4Reqmtj9L3odk/Vo2p5vF/FwztjL1\nty8ECH/JWjL7NJhZOSDT4eVC96OgJkrWyjA11JKzSRRNGc/3Tvcy4i9tDtNb4gi3\nWRDiX1YnrA//Nbbz1Z2Q3TvMSZFqxj3pm8SbrbBnwO6TyCr/GLbZZg==\n-----END RSA PRIVATE KEY-----'  # noqa: E501
    key = RSA.import_key(rsa_key_pem)
    id_opt = id_from_public_key(key.publickey())
    host = await new_node(
        transport_opt=[transport_opt],
        id_opt=id_opt,
    )
    # FIXME: should add it in KeyBook, but it doesn't exist for now.
    host.privkey = key

    await host.get_network().listen(multiaddr.Multiaddr(transport_opt))
    # support Identify
    id_service = id_protocol.IdentifyService(host=host)
    host.set_stream_handler(id_protocol.PROTOCOL_ID, id_service.request_handler)

    if not destination:  # its the server
        async def stream_handler(stream):
            asyncio.ensure_future(read_data(stream))
            asyncio.ensure_future(write_data(stream))
            print(f"!@# new stream {stream}")
        host.set_stream_handler(PROTOCOL_ID, stream_handler)

        if not port:
            raise RuntimeError("was not able to find the actual local port")

        print("Run './examples/chat/chat.py -p %s -d /ip4/%s/tcp/%s/p2p/%s' on another console.\n" %
              (int(port) + 1, external_ip, port, host.get_id().pretty()))
        print("\nWaiting for incoming connection\n\n")

    else:  # its the client
        m = multiaddr.Multiaddr(destination)
        info = info_from_p2p_addr(m)
        # Associate the peer with local ip address
        print(f"!@# try connecting {info}")
        await host.connect(info)
        print("!@# finish connecting")

        # Start a stream with the destination.
        # Multiaddress of the destination peer is fetched from the peerstore using 'peerId'.
        # stream = await host.new_stream(info.peer_id, [PROTOCOL_ID])

        # asyncio.ensure_future(read_data(stream))
        # asyncio.ensure_future(write_data(stream))
        # print("Connected to peer %s" % info.addrs[0])


@click.command()
@click.option('--port', '-p', help='source port number', default=8000)
@click.option('--destination', '-d', help="Destination multiaddr string")
@click.option('--help', is_flag=True, default=False, help='display help')
# @click.option('--debug', is_flag=True, default=False, help='Debug generates the same node id_protocol on every execution')
def main(port, destination, help):

    if help:
        print("This program demonstrates a simple p2p chat application using libp2p\n\n")
        print("Usage: Run './chat -p <SOURCE_PORT>' where <SOURCE_PORT> can be any port number.")
        print("Now run './chat -p <PORT> -d <MULTIADDR>' where <MULTIADDR> is multiaddress of previous listener host.")
        return

    loop = asyncio.get_event_loop()
    try:
        asyncio.ensure_future(run(port, destination))
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == '__main__':
    main()
