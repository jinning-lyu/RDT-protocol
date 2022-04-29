from socket import *
import argparse
from packet import Packet
from threading import Timer, Thread, Lock

# initialize to dummy values for sanity checking purposes
emulator_addr = None  # host address of the network emulator
# UDP port number used by the emulator to receive data from the sender
emulator_recv_port = None
# UDP port number used by the sender to receive SACKs from the emulator
sender_recv_port = None
timeout_interval = None  # timeout interval in units of millisecond
file_name = None  # name of the file to be transferred


def timeout(seqnum, packet):
    global timestamp
    global window
    global N
    global N_log
    global i
    global seqnum_log
    lock.acquire()
    # packet has not been acked when timer is out
    # change window size to 1
    # increase time stamp by 1
    if seqnum in window and window[seqnum]['ack'] == False:
        timestamp += 1
        N = 1
        N_log.write("t="+str(timestamp)+' ' + str(N) + '\n')
        print("timeout" + str(seqnum))
        print(str(timestamp))
        # the timeout packet is the base packet
        # retransmit the packet immediately and start a new timer
        if seqnum == SOW % 32:
            i = SOW + 1
            seqnum_log.write("t=" + str(timestamp) + ' ' + str(seqnum) + '\n')
            lock.release()
            sock.sendto(packet.encode(), (emulator_addr, emulator_recv_port))
            startTimer(seqnum, packet)
        # the timeout packet is not the base packet
        # wait until it re-enters the window
        else:
            window[seqnum]['timeout'] = True
            i = SOW
            lock.release()
    else:
        lock.release()


def startTimer(seqnum, packet):
    timer = Timer(timeout_interval/1000, timeout, [seqnum, packet])
    timer.start()


def receivePacket():
    global timestamp
    global ack_log
    global window
    global N
    global N_log
    global SOW
    global i
    while True:
        # packet size is 512 bytes maximum
        recvd_data = sock.recvfrom(512)[0]
        lock.acquire()
        if recvd_data != '':
            recvd_ack = Packet(recvd_data)
            # received EOT packet
            # increase time stamp by 1
            # this marks the end of the sender program
            if recvd_ack.decode()[0] == 2:
                timestamp += 1
                ack_log.write("t="+str(timestamp)+' EOT\n')
                lock.release()
                break
            # received SACK
            # increase time stamp by 1
            if recvd_ack.decode()[0] == 0:
                ack_seqnum = recvd_ack.decode()[1]
                timestamp += 1
                ack_log.write("t="+str(timestamp)+' ' + str(ack_seqnum) + '\n')
                # the received SACK is new
                # increase window size by 1 (capped at 10)
                if ack_seqnum in window and window[ack_seqnum]['ack'] == False:
                    window[ack_seqnum]['ack'] = True
                    N = min(N+1, 10)
                    N_log.write("t="+str(timestamp)+' ' + str(N) + '\n')
                    # the received SACK is the base packet
                    # slide the window until the base packet is the first un-acked packet
                    if SOW % 32 == ack_seqnum:
                        while (SOW % 32) in window and window[(SOW % 32)]['ack']:
                            del window[(SOW % 32)]
                            SOW += 1
                        i = max(SOW, i)
        lock.release()
    sock.close()


def sendPacket():
    global i
    global timestamp
    global seqnum_log
    global window

    ended = False
    # open the file to be transferred
    # slice the text into chunks of size 500
    with open(file_name, 'r') as file:
        text = file.read()
    chunks, chunk_size = len(text), 500
    data_ls = [text[i:i+chunk_size] for i in range(0, chunks, chunk_size)]

    while not ended:
        lock.acquire()
        # all the data chunks have been sent at lease once
        if i >= len(data_ls):
            # all the data packets have receiced SACKs
            # file has been transferred successfully
            # send EOT packet
            # increase time stamp by 1
            if len(window) == 0:
                packet = Packet(2, seqnum, 0, "")
                sock.sendto(packet.encode(),
                            (emulator_addr, emulator_recv_port))
                ended = True
                timestamp += 1
                seqnum_log.write("t=" + str(timestamp) + ' EOT \n')
            lock.release()
        else:
            # there are still data chunks in the window waiting to be sent
            while (i - SOW) < N and i < len(data_ls):
                seqnum = i % 32
                data = data_ls[i]
                packet = Packet(1, seqnum, len(data), data)
                # new packet to be sent
                # increase time stamp by 1
                if seqnum not in window:
                    window[seqnum] = {'ack': False, 'timeout': False}
                    timestamp += 1
                # timeout packet to be sent
                # do not increase time stamp
                elif window[seqnum]['ack'] == False and window[seqnum]['timeout'] == True:
                    window[seqnum]['timeout'] = False
                # skip packets that have not timed out
                else:
                    i += 1
                    lock.release()
                    lock.acquire()
                    continue
                i += 1
                seqnum_log.write("t=" + str(timestamp) +
                                 ' ' + str(seqnum) + '\n')
                lock.release()
                # send the packet to emulator
                sock.sendto(packet.encode(),
                            (emulator_addr, emulator_recv_port))
                startTimer(seqnum, packet)
                lock.acquire()
            lock.release()


if __name__ == '__main__':
    # Parse args
    parser = argparse.ArgumentParser()
    parser.add_argument("<Emulator's network address>")
    parser.add_argument("<Emulator's receiving UDP port number>",
                        help="UDP port number used by the emulator to receive data from the sender")
    parser.add_argument("<Sender's receiving UDP port number>",
                        help="UDP port number used by the sender to receive SACKs from the emulator")
    parser.add_argument("<Timeout interval>",
                        help="timeout interval in units of millisecond")
    parser.add_argument(
        "<File name>", help="name of the file to be transferred")
    args = parser.parse_args()
    args = args.__dict__  # A LAZY FIX
    emulator_addr = str(args["<Emulator's network address>"])
    emulator_recv_port = int(args["<Emulator's receiving UDP port number>"])
    sender_recv_port = int(args["<Sender's receiving UDP port number>"])
    timeout_interval = int(args["<Timeout interval>"])
    file_name = str(args["<File name>"])

    # create a lock object
    lock = Lock()
    # initialize global variables
    N = 1  # window size
    i = 0  # index of the first packet that is waiting to be sent
    SOW = 0  # start of the window (index of the base packet)
    window = {}  # packets in the window of size N
    timestamp = 0  # timestamp to be written into log files
    # set up udp socket
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(("", sender_recv_port))
    # open log files for writing
    seqnum_log = open("seqnum.log", "w")
    ack_log = open("ack.log", "w")
    N_log = open("N.log", "w")
    # N.log will have t=0 1 as the first line in the log
    N_log.write("t=0 1 \n")
    # start two threads, one for receiving SACKs, the other for sending data packets
    t1 = Thread(target=receivePacket)
    t2 = Thread(target=sendPacket)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    # close log files after data transfer is done
    seqnum_log.close()
    ack_log.close()
    N_log.close()
