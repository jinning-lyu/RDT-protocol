The program is used to send files from one host to another over UDP. It handles packet loss and packet delay with selective repeat RDT protocol.

The program can be executed by running the following commands:

1. On the host host1: `python3 network_emulator.py <port1> <host2> <port4> <port3> <host3> <port2> <max delay> <discard probability> 0`
2. On the host host2: `python3 receiver.py <host1> <port3> <port4> <output file>`
3. On the host host3: `python3 sender.py <host1> <port1> <port2> <timeout interval> <input file>`

Find usage instructions using `python3 sender.py -h` and `python3 receiver.py -h`.

NOTE: due to multithreading and locks used in sender.py, the timed out packets may not follow the correct sequence. For example, packet 1 is sent followed by packet 2. In this case, packet 1 times out before packet 2. However, if both packets time out before another thread releases the lock, then they will wait for the lock to be released. As soon as the lock is released, one of them will acquire the lock and do timeout handling. Unfortunately, this process is random, which means that packet 2 could acquire the lock before packet 1 even though theoratically packet 1 times out before packet 2. 