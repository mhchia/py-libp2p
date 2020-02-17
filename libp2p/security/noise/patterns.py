from abc import ABC, abstractmethod

from noise.connection import Keypair as NoiseKeypair
from noise.connection import NoiseConnection as NoiseState

from libp2p.crypto.ed25519 import Ed25519PublicKey
from libp2p.crypto.keys import PrivateKey
from libp2p.network.connection.raw_connection_interface import IRawConnection
from libp2p.peer.id import ID
from libp2p.security.secure_conn_interface import ISecureConn

from .connection import NoiseConnection
from .exceptions import (
    HandshakeHasNotFinished,
    InvalidSignature,
    NoiseStateError,
    PeerIDMismatchesPubkey,
)
from .io import encode_msg_body, decode_msg_body, NoiseHandshakeReadWriter
from .messages import (
    NoiseHandshakePayload,
    make_handshake_payload_sig,
    verify_handshake_payload_sig,
)


class IPattern(ABC):
    @abstractmethod
    async def handshake_inbound(self, conn: IRawConnection) -> ISecureConn:
        ...

    @abstractmethod
    async def handshake_outbound(
        self, conn: IRawConnection, remote_peer: ID
    ) -> ISecureConn:
        ...


class BasePattern(IPattern):
    protocol_name: bytes
    noise_static_key: PrivateKey
    local_peer: ID
    libp2p_privkey: PrivateKey
    early_data: bytes

    def create_noise_state(self) -> NoiseState:
        noise_state = NoiseState.from_name(self.protocol_name)
        noise_state.set_keypair_from_private_bytes(
            NoiseKeypair.STATIC, self.noise_static_key.to_bytes()
        )
        return noise_state

    def make_handshake_payload(self) -> NoiseHandshakePayload:
        signature = make_handshake_payload_sig(
            self.libp2p_privkey, self.noise_static_key.get_public_key()
        )
        return NoiseHandshakePayload(self.libp2p_privkey.get_public_key(), signature)

    async def write_msg(self, conn: IRawConnection, data: bytes) -> None:
        noise_msg = encode_msg_body(data)
        data_encrypted = self.noise_state.write_message(noise_msg)
        await self.read_writer.write_msg(data_encrypted)

    async def read_msg(self) -> bytes:
        noise_msg_encrypted = await self.read_writer.read_msg()
        noise_msg = self.noise_state.read_message(noise_msg_encrypted)
        return decode_msg_body(noise_msg)


class PatternXX(BasePattern):
    def __init__(
        self,
        local_peer: ID,
        libp2p_privkey: PrivateKey,
        noise_static_key: PrivateKey,
        early_data: bytes = None,
    ) -> None:
        self.protocol_name = b"Noise_XX_25519_ChaChaPoly_SHA256"
        self.local_peer = local_peer
        self.libp2p_privkey = libp2p_privkey
        self.noise_static_key = noise_static_key
        self.early_data = early_data

    async def handshake_inbound(self, conn: IRawConnection) -> ISecureConn:
        noise_state = self.create_noise_state()
        noise_state.set_as_responder()
        noise_state.start_handshake()
        handshake_state = noise_state.noise_protocol.handshake_state
        read_writer = NoiseHandshakeReadWriter(conn, noise_state)

        # Consume msg#1.
        await read_writer.read_msg()

        # Send msg#2, which should include our handshake payload.
        our_payload = self.make_handshake_payload()
        msg_2 = our_payload.serialize()
        await read_writer.write_msg(msg_2)

        # Receive and consume msg#3.
        msg_3 = await read_writer.read_msg()
        peer_handshake_payload = NoiseHandshakePayload.deserialize(msg_3)

        if handshake_state.rs is None:
            raise NoiseStateError(
                "something is wrong in the underlying noise `handshake_state`: "
                "we received and consumed msg#3, which should have included the"
                " remote static public key, but it is not present in the handshake_state"
            )
        # Use `Ed25519PublicKey` since 25519 is used in our pattern.
        remote_pubkey = Ed25519PublicKey.from_bytes(handshake_state.rs.public_bytes)
        if not verify_handshake_payload_sig(peer_handshake_payload, remote_pubkey):
            raise InvalidSignature
        remote_peer_id_from_pubkey = ID.from_pubkey(peer_handshake_payload.id_pubkey)

        if not noise_state.handshake_finished:
            raise HandshakeHasNotFinished(
                "handshake is done but it is not marked as finished in `noise_state`"
            )

        return NoiseConnection(
            self.local_peer,
            self.libp2p_privkey,
            remote_peer_id_from_pubkey,
            conn,
            False,
            noise_state,
        )

    async def handshake_outbound(
        self, conn: IRawConnection, remote_peer: ID
    ) -> ISecureConn:
        noise_state = self.create_noise_state()

        read_writer = NoiseHandshakeReadWriter(conn, noise_state)
        noise_state.set_as_initiator()
        noise_state.start_handshake()
        handshake_state = noise_state.noise_protocol.handshake_state

        # Send msg#1, which is *not* encrypted.
        msg_1 = b""
        await read_writer.write_msg(msg_1)

        # Read msg#2 from the remote, which contains the public key of the peer.
        msg_2 = await read_writer.read_msg()
        peer_handshake_payload = NoiseHandshakePayload.deserialize(msg_2)

        if handshake_state.rs is None:
            raise NoiseStateError(
                "something is wrong in the underlying noise `handshake_state`: "
                "we received and consumed msg#3, which should have included the"
                " remote static public key, but it is not present in the handshake_state"
            )
        # Use `Ed25519PublicKey` since 25519 is used in our pattern.
        remote_pubkey = Ed25519PublicKey.from_bytes(handshake_state.rs.public_bytes)
        if not verify_handshake_payload_sig(peer_handshake_payload, remote_pubkey):
            raise InvalidSignature
        remote_peer_id_from_pubkey = ID.from_pubkey(peer_handshake_payload.id_pubkey)
        if remote_peer_id_from_pubkey != remote_peer:
            raise PeerIDMismatchesPubkey(
                "peer id does not correspond to the received pubkey: "
                f"remote_peer={remote_peer}, "
                f"remote_peer_id_from_pubkey={remote_peer_id_from_pubkey}"
            )

        # Send msg#3, which includes our encrypted payload and our noise static key.
        our_payload = self.make_handshake_payload()
        msg_3 = our_payload.serialize()
        await read_writer.write_msg(msg_3)

        if not noise_state.handshake_finished:
            raise HandshakeHasNotFinished(
                "handshake is done but it is not marked as finished in `noise_state`"
            )

        return NoiseConnection(
            self.local_peer, self.libp2p_privkey, remote_peer, conn, False, noise_state
        )
