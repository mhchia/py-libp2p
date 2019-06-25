from libp2p.security.security_multistream import SecurityMultistream
from libp2p.security.secure_conn_interface import ISecureConn
from libp2p.stream_muxer.muxed_multistream import (
    MuxedMultistream,
)


class TransportUpgrader:
    # pylint: disable=no-self-use

    security_multistream: SecurityMultistream
    muxed_multistream: MuxedMultistream

    def __init__(self, secOpt, muxerOpt):
        # secOpt = {"insecure/1.0.0": InsecureTransport("insecure")}
        # Store security option
        self.security_multistream = SecurityMultistream()
        for key, value in secOpt.items():
            self.security_multistream.add_transport(key, value)
        # Store muxer option
        # muxerOpt = ["mplex/6.7.0"]
        # /yamux/1.0.0 /mplex/6.7.0
        self.muxed_multistream = MuxedMultistream()
        for key, value in muxerOpt.items():
            self.muxed_multistream.add_transport(key, value)

    def upgrade_listener(self, transport, listeners):
        """
        Upgrade multiaddr listeners to libp2p-transport listeners
        """

    async def upgrade_security(self, raw_conn, peer_id, initiator):
        """
        Upgrade conn to be a secured connection
        """
        if initiator:
            return await self.security_multistream.secure_outbound(raw_conn, peer_id)

        return await self.security_multistream.secure_inbound(raw_conn)

    async def upgrade_connection(
            self,
            conn: ISecureConn,
            generic_protocol_handler,
            peer_id,
            initiator):
        """
        Upgrade conn to be a muxed connection
        """

        # For PoC, no security, default to mplex
        # TODO do exchange to determine multiplexer
        return await self.muxed_multistream.new_conn(
            conn,
            generic_protocol_handler,
            peer_id,
            initiator,
        )
