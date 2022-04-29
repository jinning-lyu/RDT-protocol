from socket import *
import argparse
from packet import Packet

# initialize to dumby values for sanity checking purposes
emulator_addr = None  # host address of the network emulator
# UDP port number used by the link emulator to receive ACKs from the receiver
emulator_recv_port = None
# UDP port number used by the receiver to receive data from the emulator
receiver_recv_port = None
file_name = None  # name of the file into which the received data is written


def ackPacket():
    # initialize buffer and SOW (start of window)
    buffer = {}
    SOW = 0
    # set up UDP socket
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(('', receiver_recv_port))
    # open output and log files for writing
    output = open(file_name, "w")
    arrival_log = open("arrival.log", "w")
    while True:
        # receive packet from emulator
        recvd_packet = Packet(sock.recvfrom(512)[0])
        # check packet type
        if recvd_packet.decode()[0] == 2:
            # log received EOT packet and send it back to emulator
            # this marks the end of data transfer
            sock.sendto(recvd_packet.encode(),
                        (emulator_addr, emulator_recv_port))
            arrival_log.write('EOT\n')
            break
        elif recvd_packet.decode()[0] == 1:
            # log received data packet
            seqnum = recvd_packet.decode()[1]
            data = recvd_packet.decode()[3]
            arrival_log.write(str(seqnum) + '\n')
            window = [s % 32 for s in range(SOW, SOW+10, 1)]
            last_10 = [s % 32 for s in range(SOW-1, SOW-11, -1)]
            # check if seqnum is in the window of size 10
            if seqnum in window:
                # put data into buffer
                # send SACK packet to emulator
                buffer[seqnum] = data
                packet = Packet(0, seqnum, 0, '')
                sock.sendto(packet.encode(),
                            (emulator_addr, emulator_recv_port))
                # check if seqnum is SOW
                if seqnum == SOW % 32:
                    # write the data in the packet and any previously buffered and consecutively numbered packets to the file
                    # and remove those packets from the buffer
                    while SOW % 32 in buffer:
                        output.write(buffer[SOW % 32])
                        del buffer[SOW % 32]
                        SOW += 1
            # sequence number is within the last 10 consecutive sequence numbers of the base of the window
            elif seqnum in last_10:
                # send SACK packet to emulator
                # discard the packet
                packet = Packet(0, seqnum, 0, '')
                sock.sendto(packet.encode(),
                            (emulator_addr, emulator_recv_port))
    # close files and UDP
    output.close()
    arrival_log.close()
    sock.close()


if __name__ == '__main__':
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("<Emulator's network address>")
    parser.add_argument("<Emulator's receiving UDP port number>",
                        help="UDP port number used by the link emulator to receive ACKs from the receiver")
    parser.add_argument("<Receiver's receiving UDP port number>",
                        help="UDP port number used by the receiver to receive data from the emulator")
    parser.add_argument(
        "<File name>", help="name of the file into which the received data is written")
    args = parser.parse_args()
    args = args.__dict__  # A LAZY FIX
    emulator_addr = str(args["<Emulator's network address>"])
    emulator_recv_port = int(args["<Emulator's receiving UDP port number>"])
    receiver_recv_port = int(args["<Receiver's receiving UDP port number>"])
    file_name = str(args["<File name>"])

    ackPacket()
