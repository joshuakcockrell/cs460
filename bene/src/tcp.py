from .buffer import SendBuffer, ReceiveBuffer
from .connection import Connection
from .sim import Sim
from .tcppacket import TCPPacket


class TCP(Connection):
    """ A TCP connection between two hosts."""

    def __init__(self, transport, source_address, source_port,
                 destination_address, destination_port, app=None, window=1000,drop=[]):
        Connection.__init__(self, transport, source_address, source_port,
                            destination_address, destination_port, app)

        # -- Sender functionality

        # send window; represents the total number of bytes that may
        # be outstanding at one time
        self.window = window
        # send buffer
        self.send_buffer = SendBuffer()
        # maximum segment size, in bytes
        # self.mss = 1000
        self.mss = 1
        # largest sequence number that has been ACKed so far; represents
        # the next sequence number the client expects to receive
        self.sequence = 0
        # plot sequence numbers
        self.plot_sequence_header()
        # packets to drop
        self.drop = drop
        self.dropped = []
        # retransmission timer
        self.timer = None
        # timeout duration in seconds
        self.timeout = 1

        # -- Receiver functionality

        # receive buffer
        self.receive_buffer = ReceiveBuffer()
        # ack number to send; represents the largest in-order sequence
        # number not yet received
        self.ack = 0

    def trace(self, message):
        """ Print debugging messages. """
        Sim.trace("TCP", message)

    def plot_sequence_header(self):
        if self.node.hostname =='n1':
            Sim.plot('sequence.csv','Time,Sequence Number,Event\n')

    def plot_sequence(self,sequence,event):
        if self.node.hostname =='n1':
            Sim.plot('sequence.csv','%s,%s,%s\n' % (Sim.scheduler.current_time(),sequence,event))

    def receive_packet(self, packet):
        print ''
        print 'RECEIVE DATA'
        print 'ack',packet.ack_number
        print 'seq',packet.sequence

        """ Receive a packet from the network layer. """
        # if packet.ack_number > 0:
            # handle ACK
        self.handle_ack(packet)
        if packet.length > 0:
            # handle data
            self.handle_data(packet)

    ''' Sender '''
    def send_on_ack(self):

        if not self.send_buffer.available():
            return

        print ''
        print 'SEND DATA'

        current_window = self.window - self.send_buffer.outstanding()
        while (current_window > 0):
            next_data = self.send_buffer.get(self.mss)
            print next_data
            self.send_packet(next_data[0], next_data[1])
            current_window -= self.mss

    def send(self, data):
        """ Send data on the connection. Called by the application. This
            code currently sends all data immediately. """

        print 'Load into buffer..'
        print data
        self.send_buffer.put(data)

        self.send_on_ack()

    def send_packet(self, data, sequence):
        packet = TCPPacket(source_address=self.source_address,
                           source_port=self.source_port,
                           destination_address=self.destination_address,
                           destination_port=self.destination_port,
                           body=data,
                           sequence=sequence, ack_number=self.ack)

        if sequence in self.drop and not sequence in self.dropped:
            self.dropped.append(sequence)
            self.plot_sequence(sequence,'drop')
            self.trace("%s (%d) dropping TCP segment to %d for %d" % (
                self.node.hostname, self.source_address, self.destination_address, packet.sequence))
            return

        # send the packet
        self.plot_sequence(sequence,'send')
        self.trace("%s (%d) sending TCP segment to %d for %d" % (
            self.node.hostname, self.source_address, self.destination_address, packet.sequence))
        self.transport.send_packet(packet)

        # set a timer
        if not self.timer:
            self.timer = Sim.scheduler.add(delay=self.timeout, event='sequence_' + sequence + 'timeout', handler=self.retransmit)

    def handle_ack(self, packet):
        """ Handle an incoming ACK. """
        self.plot_sequence(packet.ack_number - 1000,'ack')
        self.trace("%s (%d) received ACK from %d for %d" % (
            self.node.hostname, packet.destination_address, packet.source_address, packet.ack_number))
        # self.cancel_timer() # TODO FIX
        self.send_buffer.slide(packet.ack_number)
        self.send_on_ack()

    def retransmit(self, event):
        """ Retransmit data. """
        print event
        self.trace("%s (%d) retransmission timer fired" % (self.node.hostname, self.source_address))

    def cancel_timer(self):
        """ Cancel the timer. """
        if not self.timer:
            return
        Sim.scheduler.cancel(self.timer)
        self.timer = None

    ''' Receiver '''

    def handle_data(self, packet):
        """ Handle incoming data. This code currently gives all data to
            the application, regardless of whether it is in order, and sends
            an ACK."""
        self.trace("%s (%d) received TCP segment from %d for %d" % (
            self.node.hostname, packet.destination_address, packet.source_address, packet.sequence))

        self.receive_buffer.put(packet.body, packet.sequence)

        self.app.receive_data(packet.body) # send to app
        print 'handle_data'
        print packet.sequence + len(packet.body)

        self.ack = packet.sequence + len(packet.body) # highest consec weve seen
        self.send_ack()

    def send_ack(self):
        """ Send an ack. """
        packet = TCPPacket(source_address=self.source_address,
                           source_port=self.source_port,
                           destination_address=self.destination_address,
                           destination_port=self.destination_port,
                           sequence=self.sequence, ack_number=self.ack)
        # send the packet
        self.trace("%s (%d) sending TCP ACK to %d for %d" % (
            self.node.hostname, self.source_address, self.destination_address, packet.ack_number))
        self.transport.send_packet(packet)






