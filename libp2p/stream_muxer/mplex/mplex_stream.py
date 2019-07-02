import asyncio
from io import BytesIO

from .utils import get_flag
from ..muxed_stream_interface import IMuxedStream


class MplexStream(IMuxedStream):
    # pylint: disable=too-many-instance-attributes
    """
    reference: https://github.com/libp2p/go-mplex/blob/master/stream.go
    """

    buf: bytes

    def __init__(self, stream_id, initiator, mplex_conn):
        """
        create new MuxedStream in muxer
        :param stream_id: stream stream id
        :param initiator: boolean if this is an initiator
        :param mplex_conn: muxed connection of this muxed_stream
        """
        self.stream_id = stream_id
        self.initiator = initiator
        self.mplex_conn = mplex_conn
        self.read_deadline = None
        self.write_deadline = None
        self.local_closed = False
        self.remote_closed = False
        self.stream_lock = asyncio.Lock()
        self.buf = None

    async def read(self, n: int = -1) -> bytes:
        """
        read messages associated with stream from buffer til end of file
        :return: bytes of input
        """
        if n == -1:
            return await self.mplex_conn.read_buffer(self.stream_id)
        return await self.read_bytes(n)

    async def read_bytes(self, n: int) -> bytes:
        if self.buf is None:
            self.buf = await self.mplex_conn.read_buffer(self.stream_id)
        n_read = 0
        bytes_buf = BytesIO()
        while self.buf is not None and n_read < n:
            n_to_read = min(n - n_read, len(self.buf))
            bytes_buf.write(self.buf[:n_to_read])
            if n_to_read == n - n_read:
                self.buf = self.buf[n_to_read:]
            else:
                self.buf = None
                self.buf = await self.mplex_conn.read_buffer(self.stream_id)
            n_read += n_to_read
        return bytes_buf.getvalue()

    async def write(self, data):
        """
        write to stream
        :return: number of bytes written
        """
        return await self.mplex_conn.send_message(
            get_flag(self.initiator, "MESSAGE"), data, self.stream_id)

    async def close(self):
        """
        Closing a stream closes it for writing and closes the remote end for reading
        but allows writing in the other direction.
        :return: true if successful
        """
        # TODO error handling with timeout
        # TODO understand better how mutexes are used from go repo
        await self.mplex_conn.send_message(get_flag(self.initiator, "CLOSE"), None, self.stream_id)

        remote_lock = ""
        async with self.stream_lock:
            if self.local_closed:
                return True
            self.local_closed = True
            remote_lock = self.remote_closed

        if remote_lock:
            async with self.mplex_conn.conn_lock:
                self.mplex_conn.buffers.pop(self.stream_id)

        return True

    async def reset(self):
        """
        closes both ends of the stream
        tells this remote side to hang up
        :return: true if successful
        """
        # TODO understand better how mutexes are used here
        # TODO understand the difference between close and reset
        async with self.stream_lock:
            if self.remote_closed and self.local_closed:
                return True

            if not self.remote_closed:
                await self.mplex_conn.send_message(
                    get_flag(self.initiator, "RESET"), None, self.stream_id)

            self.local_closed = True
            self.remote_closed = True

        async with self.mplex_conn.conn_lock:
            self.mplex_conn.buffers.pop(self.stream_id, None)

        return True

    # TODO deadline not in use
    def set_deadline(self, ttl):
        """
        set deadline for muxed stream
        :return: True if successful
        """
        self.read_deadline = ttl
        self.write_deadline = ttl
        return True

    def set_read_deadline(self, ttl):
        """
        set read deadline for muxed stream
        :return: True if successful
        """
        self.read_deadline = ttl
        return True

    def set_write_deadline(self, ttl):
        """
        set write deadline for muxed stream
        :return: True if successful
        """
        self.write_deadline = ttl
        return True
