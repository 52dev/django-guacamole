import socket
import logging
import itertools
from django.conf import settings


logger = logging.getLogger(__name__)


class ProtocolError(Exception):
    pass


class Instruction(object):
    def __init__(self, opcode, *args):
        self.opcode = opcode
        self.args = args

    @classmethod
    def deserialize(cls, serialized):
        last = serialized[-1]
        if last != ';':
            raise ProtocolError('Invalid instruction format.')

        tokens = serialized[:-1].split(',')

        def decode_arg(pair):
            length, arg = pair.split('.')
            if len(arg) != int(length):
                raise ProtocolError('Invalid format')

            return arg

        args = [decode_arg(t) for t in tokens]
        return cls(args[0], *args[1:])

    def serialize(self):
        """Serializes an instruction for sending over the wire.
        """
        def encode_arg(arg):
            arg = str(arg)
            return '%s.%s' % (len(arg), arg)

        content = ','.join(encode_arg(a)
                           for a in itertools.chain([self.opcode], self.args))
        return content + ';'


class GuacamoleClient(object):
    def __init__(self, host=settings.GUACD_HOST, port=settings.GUACD_PORT,
                 timeout=15):
        self.socket = socket.create_connection((host, port), timeout)
        self._buffer = bytearray()

    def close(self):
        self.socket.close()

    def read(self):
        start = 0
        while True:
            index = self._buffer.find(';', start)
            if index != -1:
                line = str(self._buffer[:index + 1])
                self._buffer = self._buffer[index + 1:]
                logger.debug('R: %s', line)
                return line
            else:
                start = len(self._buffer)
                buf = self.socket.recv(4096)
                if not buf:
                    logger.debug('Connection has been closed.')
                    self.close()
                    return None
                self._buffer.extend(buf)

    def readinstruction(self):
        return Instruction.deserialize(self.read())

    def write(self, content):
        logger.debug('W: %s', content)
        self.socket.sendall(content)

    def writeinstruction(self, instruction):
        self.write(instruction.serialize())

    def connect(self, **kwargs):
        self.writeinstruction(Instruction('select', kwargs['protocol']))

        while True:
            instruction = self.readinstruction()
            if not instruction:
                raise ProtocolError('End of stream during initial handshake.')
            if instruction.opcode == 'args':
                break

        values = [kwargs.get(a.replace('-', '_'), '')
                  for a in instruction.args]

        self.writeinstruction(Instruction('size', 640, 480))
        self.writeinstruction(Instruction('audio', ''))
        self.writeinstruction(Instruction('video', ''))
        self.writeinstruction(Instruction('connect', *values))
