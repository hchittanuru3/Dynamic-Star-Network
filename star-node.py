import sys
import os
import socket
import threading
import time
from socket import error as SocketError
import errno

global name  # Name of this star-node
global hubNode  # The name of the current hub node
global addrDict  # Dictionary storing known active star-nodes and their addresses
global RTTdict # Dictionary storing known active star-nodes and their RTT measurements
global RTTNumDict # Dictionary storing how many RTT responses each node gets (For running average calculation)
global RTTSumDict # Dictionary storing the RTT sums for all the known active star-nodes
global local_address # A tuple of the IP and port this star-node is running on
global conn # A UDP socket object bound to the address of this star-node
global POC_address # A tuple of the IP and port of this node's POC
global n # Maximum number of nodes in the network
global online # Whether the node is online or not
global poc_response # Whether or not the POC responded
global sendAckDict # Dictionary to store whether an ACK has been received from a node after sending a message/file
global aliveDict # Dictionary to store whether a node is alive or not
global sumAckDict # Dictionary to store whether an ACK has been received from a node after
global nodeAckDict # Dictionary to store whether an ACK
global receivedSet # A set of the messages/files that the node receives
global rtt_response_set # A set of the nodes that the node has gotten RTT responses from

# Calculate whether the node is alive or not
def keepAlive(node):
    global aliveDict
    while online:
        time.sleep(10)
        lastTime = aliveDict[node]
        if time.time() - lastTime > 15:
            f = open("log.txt", "a")
            f.write(str(time.ctime(time.time())) + ": Star Node "+ node + " is offline.\n")
            f.close()
            removeNode(node)
            break


# Forwards any messages sent to the hub node to all the discovered nodes.
def hubNodePropagation(message, sender):
    global addrDict, name, sendAckDict
    for k, v in addrDict.items():
        if not online:
            break
        if k != sender:
            sendAckDict[k] = False
            threadName = "Check send ACK from " + k
            t = threading.Thread(name=threadName, target=checkSendAck, args=[message, time.time(), k])
            t.start()
            conn.sendto(message, v)
        #Logs the event of getting forwarding a message from the hub node
            f = open("log.txt", "a")
            log = str(time.ctime(time.time())) + ": Message forwarded from " + name + " to " + str(k) + ".\n"
            f.write(log)

# Re-Calculates the RTT Sum for the current node, then sents the RTT Sum to all the discovered nodes.
def startRTTSumCalculation():
    global name, sumAckDict, addrDict, RTTSumDict
    RTTSumCalculation()
    for key, address in addrDict.items():
        if not online:
            break
        packet = "RTT Sum from " + name + " is: " + str(RTTSumDict[name])
        packet = packet.encode("ASCII")
        threadName = "Check Sum ACK from " + key
        sumAckDict[key] = False
        t = threading.Thread(name=threadName, target=checkSumAck, args=[packet, time.time(), key])
        t.start()
        conn.sendto(packet, address)

# Calculates the RTT Sum for the current node (sums the RTT values for all the discovered nodes)
def RTTSumCalculation():
    global RTTdict, RTTSumDict, name
    #Re-calculates the RTTSum value for the current node
    rttsum = 0
    for key, value in RTTdict.items():
        rttsum += value
    RTTSumDict[name] = rttsum
    # Logs that a new RTT Sum is has been calculated.
    f = open("log.txt", "a")
    log = str(time.ctime(time.time())) + ": The new RTT Sum for " + name + " is " + str(rttsum) + ".\n"
    f.write(log)
    f.close()
    selectHubNode()

# Periodically calculates (every 5 seconds) the RTT value from the sending node to another node.
def RTTCalculation(contactNode, address):
    global addrDict, RTTdict, n, online
    while contactNode in addrDict.keys() and online:
        try:
            send_time = time.time()
            message = "RTT Request from " + name + " at " + str(send_time)
            message = message.encode("ASCII")
            conn.sendto(message, address)
            time.sleep(3)
        except OSError:
            pass

# Displays the current status of a node (the active nodes, the RTT values, and the current hub node).
def showStatus():
    global RTTdict, hubNode
    if len(RTTdict) == 0:
        print("No other nodes have been discovered.")
    else:
        print("These are the known active star-nodes and their RTT measurement values.")
        for k in RTTdict.keys():
            print(k + ": " + str(RTTdict[k]))
    print("The hub star-node is currently: " + str(hubNode))

# Displays the log file.
def showLog():
    f = open("log.txt", "r")
    if f.mode == "r":
        print(f.read())

# Sends the info in the current node knows about the network (values in the addrDict) to another node.
def sendNodeInfo(node, addr):
    global addrDict, nodeAckDict
    copyDict = addrDict.copy()
    for k, v in copyDict.items():
        if not online:
            break
        if node != k:
            message = "Node in network: " + str(k) + " " + str(v)
            message = message.encode("ASCII")
            nodeAckDict[node] = False
            while not nodeAckDict[node]:
                conn.sendto(message, addr)
                time.sleep(5)

#Probes (by sending POC Created packets) to check the POC of the current node to create a connection.
def tellPOC(addrTup):
    global conn, name, poc_response
    #Times out after a minute of probing.
    timeout = time.time() + 60
    while not poc_response:
        if time.time() > timeout:
            print("Timeout Error: POC Not Found")
            break
        message = "POC Created: " + name + " has been created"
        message = message.encode("ASCII")
        try:
            conn.sendto(message, addrTup)
        except SocketError:
            pass
        time.sleep(5)

# Checks for any packets being sent to the node and determines the appropriate response.
# A thread that always runs in the background, until the node is closed.
def processMessages():
    global addrDict, name, RTTdict, conn, POC_address, online, poc_response, hubNode, aliveDict, sendAckDict, sumAckDict, rtt_response_set, RTTNumDict, nodeAckDict
    while online:
        try:
            # Splits up the packet from the address sent.
            message, address = conn.recvfrom(2048)
            # A packet is received
            recvTime = time.time()
            origMessage = message
            # Splits the packet by "^" in order to handle a sent file.
            fileName = message.split(b"^")
            #print(fileName[0])

            try:
                message = message.decode("ASCII")
            except:
                #print(fileName)
                pass

            #print("Received message: " + message) # For debugging

            # POC Node Discovery packet is received
            if message[:11] == "POC Created":
                arr = message.split()
                #Adds the node properly to the addrDict and initializes the connected node in the RTTdict
                addrDict[arr[2]] = address
                RTTdict[arr[2]] = 0
                RTTSumDict[arr[2]] = 0
                RTTNumDict[arr[2]] = 0
                sendAckDict[arr[2]] = False
                sumAckDict[arr[2]] = False
                nodeAckDict[arr[2]] = False
                aliveDict[arr[2]] = recvTime
                #A POC Acknowledgment packet is sent back to the initial node
                ackMessage = "POC ACK from " + name
                ackMessage = ackMessage.encode("ASCII")
                conn.sendto(ackMessage, address)
                for k, v in addrDict.items():
                    nodeAckDict[k] = False
                    tName = "Send node info to " + k
                    t = threading.Thread(name=tName, target=sendNodeInfo, args=[k,v])
                    t.start()
                #Start RTT Calculation
                threadName = "RTT from " + name + " to " + arr[2]
                t = threading.Thread(name=threadName, target=RTTCalculation, args=[arr[2], address])
                t.start()

                tName = "Keep Alive from " + name + " to " + arr[2]
                s = threading.Thread(name=tName, target=keepAlive, args=[arr[2]])
                s.start()
                #Logs the event of discovering another node
                f = open("log.txt", "a")
                f.write(str(time.ctime(recvTime)) + ": Discovered " + arr[2] + "\n")
                f.close()

            # RTT Calculation Request packet is received
            elif message[:11] == "RTT Request":
                arr = message.split()
                nodeName = arr[3]
                #threadName = "Keep Alive from " + name + " to " + nodeName
                aliveDict[nodeName] = recvTime # Kills running keep alive thread
                response = "RTT Response from " + name + " Sent Time: " + arr[5]
                response = response.encode("ASCII")
                #Logs the event of getting an RTT Request
                f = open("log.txt", "a")
                f.write(str(time.ctime(recvTime)) + ": RTT Request from " + nodeName + "\n")
                f.close()
                conn.sendto(response, address)

            # RTT Response packet is received
            elif message[:12] == "RTT Response":
                arr = message.split()
                nodeName = arr[3]
                sent_time = float(arr[6])
                RTTdict[nodeName] = ((RTTdict[nodeName] * RTTNumDict[nodeName]) + recvTime - sent_time)/(RTTNumDict[nodeName] + 1)
                RTTNumDict[nodeName] += 1
                aliveDict[nodeName] = recvTime
                #Logs the event of getting an RTT Response
                f = open("log.txt", "a")
                f.write(str(time.ctime(recvTime)) + ": RTT Response from " + nodeName + "\n")
                f.close()
                rttSetLen = len(rtt_response_set)
                rtt_response_set.add(nodeName)
                if len(rtt_response_set) > rttSetLen:
                    startRTTSumCalculation()

            # POC Acknowledgement packet is received
            elif message[:7] == "POC ACK":
                #Sets poc_response to True so that no more POC messages are sent in tellPOC()
                poc_response = True
                arr = message.split()
                #print("Found node " + arr[3])
                addrDict[arr[3]] = address
                RTTdict[arr[3]] = 0
                RTTSumDict[arr[3]] = 100
                RTTNumDict[arr[3]] = 0
                sendAckDict[arr[3]] = False
                sumAckDict[arr[3]] = False
                nodeAckDict[arr[3]] = False
                aliveDict[arr[3]] = recvTime
                #An RTTCalculation thread is created to update the RTT value for the POC.
                threadName = "RTT from " + name + " to " + arr[3]
                t = threading.Thread(name=threadName, target=RTTCalculation, args=[arr[3], address])
                t.start()
                tName = "Keep Alive from " + name + " to " + arr[3]
                s = threading.Thread(name=tName, target=keepAlive, args=[arr[3]])
                s.start()

            # Other Node Discovery packet is received
            elif message[:15] == "Node in network":
                arr = message.split()
                nodeName = arr[3]
                if nodeName not in addrDict and nodeName != name:
                    f = open("log.txt", "a")
                    f.write(str(time.ctime(recvTime)) + ": Discovered " + nodeName + "\n")
                    f.close()
                    tup1 = arr[4].strip("(")
                    tup1 = tup1.strip(",'")
                    tup2 = int(arr[5].strip(")"))
                    addrDict[nodeName] = (tup1, tup2)
                    RTTdict[nodeName] = 0
                    RTTSumDict[nodeName] = 100
                    RTTNumDict[nodeName] = 0
                    sendAckDict[nodeName] = False
                    sumAckDict[nodeName] = False
                    nodeAckDict[nodeName] = False
                    aliveDict[nodeName] = recvTime
                    for k, v in addrDict.items():
                        nodeAckDict[k] = False
                        tName = "Send node info to " + k
                        t = threading.Thread(name=tName, target=sendNodeInfo, args=[k,v])
                        t.start()
                    #An RTTCalculation thread is created to update the RTT value for the POC.
                    threadName = "RTT from " + name + " to " + nodeName
                    t = threading.Thread(name=threadName, target=RTTCalculation, args=[nodeName, addrDict[nodeName]])
                    t.start()
                    sName = "Keep Alive from " + name + " to " + nodeName
                    s = threading.Thread(name=sName, target=keepAlive, args=[nodeName])
                    s.start()
                packet = "Discovery ACK from " + name
                packet = packet.encode("ASCII")
                conn.sendto(packet, address)

            # Received ACK from node that was sent node info
            elif message[:13] == "Discovery ACK":
                arr = message.split()
                nodeAckDict[arr[3]] = True

            # Receiving a packetized message from hubNode (message)
            elif message[:8] == "1 Sender":
                if origMessage not in receivedSet:
                    receivedSet.add(origMessage)
                    #Separates data from the Message packet
                    sender, data = depacketizeMessage(message)
                    #Prints the message to the command line of the node
                    print("Message: " + data + " from " + sender)
                    #Logs the event of receiving a message
                    f = open("log.txt", "a")
                    f.write(str(time.ctime(recvTime)) + ": Message from " + sender + " received\n")
                    f.close()
                    if name == hubNode:
                        message = message.encode("ASCII")
                        hubNodePropagation(message, sender)
                ackMessage = "Message ACK from " + name
                ackMessage = ackMessage.encode("ASCII")
                conn.sendto(ackMessage, address)

            # Receiving a packetized file from hubNode (file)
            elif fileName[0].decode()[:8] == "2 Sender":
                #print("Received")
                #print(packets.split(b"^")[0].decode())
                #print(arr)
                #Separates data from the File packet
                #sender, filename, data = depacketizeFile(message.encode("ASCII"))
                if origMessage not in receivedSet:
                    receivedSet.add(origMessage)
                    arr = fileName[0].decode().split(" ")
                    sender = arr[2]
                    file_name = arr[4]
                    #Downloads the file to the node
                    f = open(file_name, 'wb')
                    f.write(fileName[1])
                    f.close()
                    #Prints the file name and sender to the command line of the node
                    print("File: " + file_name + " from " + sender + " received and downloaded")
                    #Logs the event of receiving a file
                    f = open("log.txt", "a")
                    f.write(str(time.ctime(recvTime)) + ": File " + file_name + " from " + sender + " received and downloaded\n")
                    f.close()
                    if name == hubNode:
                        hubNodePropagation(origMessage, sender)
                ackMessage = "File ACK from " + name
                ackMessage = ackMessage.encode("ASCII")
                conn.sendto(ackMessage, address)

            # Receiving acknoledgment that message was sent
            elif message[:11] == "Message ACK":
                #print("Message ACK received")
                arr = message.split()
                nodeName = arr[3]
                sendAckDict[nodeName] = True

            # Receiving acknowledgment that file was sent
            elif message[:8] == "File ACK":
                arr = message.split()
                nodeName = arr[3]
                sendAckDict[nodeName] = True

            # Handles a node is disconnecting packet and updates values accordingly.
            elif message[:13] == "Disconnecting":
                #Getting the name of the node that is disconnecting
                arr = message.split()
                #Logs the event of a node being disconnected.
                f = open("log.txt", "a")
                f.write(str(time.ctime(recvTime)) + ": Star Node "+ arr[1] + " is disconnecting.\n")
                f.close()
                #Removing the node from the data structures of known nodes
                removeNode(arr[1])

            # RTT Sum Update Packet
            elif message[:7] == "RTT Sum":
                arr = message.split()
                #Logs the event of receiving an RTT Sum packet
                f = open("log.txt", "a")
                f.write(str(time.ctime(recvTime)) + ": RTT Sum received from " + arr[3] + "\n")
                f.close()
                packets = "Sum ACK from " + name
                packets = packets.encode("ASCII")
                conn.sendto(packets, address)
                #Updates the RTT Sum value for the sending node
                RTTSumDict[arr[3]] = float(arr[5])
                selectHubNode()

            # RTT Sum ACK Packet
            elif message[:7] == "Sum ACK":
                arr = message.split()
                nodeName = arr[3]
                sumAckDict[nodeName] = True

        except OSError:
            pass

# Establishes the UDP socket connection.
def generateSocket(addr):
    global conn
    conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conn.bind(addr)
    conn.settimeout(15)

#Decides a new hub node, by finding the node with the minimum RTT sum value.
def selectHubNode():
    global hubNode, RTTSumDict
    if len(RTTSumDict.keys()) > 0:
        minRTT = sys.maxsize
        mins = []
        for k, v in RTTSumDict.items():
            if v < minRTT:
                mins = [k]
                minRTT = v
            elif v == minRTT:
                mins.append(k)
        if len(mins) == 1:
            hubNode = mins[0]
        else:
            mins.sort()
            hubNode = mins[0]

    else:
        hubNode = None

    f = open("log.txt", "a")
    f.write(str(time.ctime(time.time())) + ": " + "The new Hub Node is " + hubNode + ".\n")
    f.close()



# Remove node from data structures
def removeNode(node):
    global addrDict, RTTdict, RTTSumDict, sendAckDict, rtt_response_set
    if node in addrDict:
        del addrDict[node]
        del RTTdict[node]
        del RTTSumDict[node]
        sendAckDict[node] = True
        sumAckDict[node] = True
        nodeAckDict[node] = True
        rtt_response_set.remove(node)
        startRTTSumCalculation()
        selectHubNode()

# Disconnects the node and closes the socket connection.
def disconnect():
    global conn, name, addrDict, online
    # Send the message that node is disconnecting to POC
    print("This star-node, " + name + " is disconnecting.")
    message = "Disconnecting: " + name
    message = message.encode("ASCII")
    for k, v in addrDict.items():
        conn.sendto(message, v)
    # Logs the event of disconnecting
    f = open("log.txt", "a")
    f.write(str(time.ctime(time.time())) + ": " + "This star-node, " + name + " is disconnecting.\n")
    f.close()
    online = False
    time.sleep(5)
    conn.close()
    exit(0)

def checkSendAck(packets, sendTime, node):
    global sendAckDict
    timeout = sendTime + 5
    while not sendAckDict[node]:
        if time.time() > timeout:
            threadName = "Check send ACK from " + str(node)
            t = threading.Thread(name=threadName, target=checkSendAck, args=[packets, time.time(), node])
            t.start()
            f = open("log.txt", "a")
            f.write(str(time.ctime(time.time())) + ": " + name + " has to retransmit message to " + node + ".\n")
            f.close()
            conn.sendto(packets, addrDict[node])
            break

def checkSumAck(packets, sendTime, node):
    global sumAckDict
    timeout = sendTime + 10
    while not sumAckDict[node]:
        if time.time() > timeout:
            threadName = "Check Sum ACK from " + str(node)
            t = threading.Thread(name=threadName, target=checkSumAck, args=[packets, time.time(), node])
            t.start()
            conn.sendto(packets, addrDict[node])
            break

# Allows the send command to send messages or files to the hub node (which is then forwarded to all the other nodes).
def send(arg):
    global conn, hubNode, addrDict, name, local_address, sendAckDict
    #Check if the file is a string or a document
    if (arg[0] == "'" and arg[-1] == "'") or (arg[0] == '"' and arg[-1] == '"') :
        #Check if the message is the correct size
        if len(arg.encode('ASCII')) < 64000:
            #Send the message
            while True:
                #The message is formatted as a packet
                arg = arg.encode('ASCII')
                packets = packetizeMessage(arg)
                if name == hubNode:
                    hubNodePropagation(packets, local_address)
                else:
                    try:
                        #Sends the message to the hub node or directly to other node if there are only 2 nodes.
                            sendAckDict[hubNode] = False
                            sendTime = time.time()
                            f = open("log.txt", "a")
                            f.write(str(time.ctime(sendTime)) + ": Sent message to " + str(hubNode) + "\n")
                            conn.sendto(packets, addrDict[hubNode])
                            threadName = "Check send ACK from " + hubNode
                            t = threading.Thread(name=threadName, target=checkSendAck, args=[packets, sendTime, hubNode])
                            t.start()
                    except OSError:
                        pass
                break
        else:
            print("This message is too big")
    elif os.path.exists(arg):
        #Check if the file is the correct size
        if os.path.getsize(arg) < 64000:
            #Send file
            while True:
                #Reads file into variable and then is formatted as packet
                f = open(arg, "rb")
                data = f.read()
                packets = packetizeFile(data, arg)
                #print(packets.split(b"^")[0])
                #print(packets.split(b"^")[0].decode())

                if name == hubNode:
                    hubNodePropagation(packets, local_address)

                else:
                    try:
                        #Sends the file to the hub node or directly to other node if there are only 2 nodes.
                        sendAckDict[hubNode] = False
                        sendTime = time.time()
                        f = open("log.txt", "a")
                        f.write(str(time.ctime(sendTime)) + ": Sent message to " + str(hubNode) + "\n")
                        threadName = "Check send ACK from " + hubNode
                        t = threading.Thread(name=threadName, target=checkSendAck, args=[packets, sendTime, hubNode])
                        t.start()
                        conn.sendto(packets, addrDict[hubNode])
                    except OSError:
                        pass
                break
        else:
            print("This file is too big")
    else:
        print("This file does not exist")

# Adds a header (sender name) to form a message packet.
def packetizeMessage(arg):
    global name
    #Takes a message and creates a formatted packet with the data.
    header = "1" + " " + "Sender:" + " " + name + " " + str(time.time()) + " "
    return header.encode('ASCII') + arg

# Takes received message and re-formats it to split the sender and message data.
def depacketizeMessage(arg):
    #Takes received message and re-formats it
    arr = arg.split(" ", 4)
    #Should return a tuple with (original sender, message data)
    return (arr[2], arr[4])

# Adds a header (sender name, filename) to form a file packet.
def packetizeFile(arg, filename):
    global name
    #Take a file and creates a formatted packet with the data.
    header = "2" + " " + "Sender:" + " " + name + " " + str(time.time()) + " " + filename + " " + "^"
    return header.encode('ASCII') + arg

def main():
    global name, hubNode, RTTdict, addrDict, RTTSumDict, POC_address, n, online, poc_response, local_address, aliveDict, sendAckDict, sumAckDict, rtt_response_set, RTTNumDict, receivedSet, nodeAckDict
    hubNode = None
    RTTdict = {}
    RTTNumDict = {}
    online = True
    poc_response = False
    rtt_started = False
    RTTSumDict = {}
    addrDict = {}
    sendAckDict = {}
    aliveDict = {}
    sumAckDict = {}
    nodeAckDict = {}
    rtt_response_set = set()
    receivedSet = set()
    # star-node.py <name> <local-port> <PoC-address> <PoC-port> <N>
    name = sys.argv[1]
    if len(name) > 16 or name == None:
        print("ERROR: Name of node has to be between 1 and 16 characters.")
        exit(0)

    local_port = int(sys.argv[2])
    if local_port < 1 or local_port > 65535:
        print("ERROR: Local port number must be between 1 and 65535.")
        exit(0)

    poc_address = sys.argv[3] # Set to 0 if node doesn't have POC
    poc_port = int(sys.argv[4]) # Set to 0 if node doesn't have POC
    if poc_port < 0 or poc_port > 65535:
        print("ERROR: POC's port number must be between 1 and 65535.")
        exit(0)
    n = int(sys.argv[5])

    print("Setting up star-node " + name)
    # Creating the log file
    try:
        f = open("log.txt", "x")
        f.close()
    except FileExistsError:
        f = open("log.txt", "w")
        f.close()

    #Initial information for setting up the UDP socket.
    IP = socket.gethostbyname(socket.gethostname())
    local_address = (IP, local_port)
    #print(local_address)
    POC_address = (poc_address, poc_port)
    generateSocket(local_address)

    #Initializes the threads for message processing
    t = threading.Thread(name='processMessages', target=processMessages)
    t.start()

    if POC_address != ('0', 0):
        tellPOC(POC_address)

    while 1:
        #print(threading.enumerate())
        command = input("Type in your command: ")
        commands = command.split(" ", 1)

        if commands[0] == 'send':
            #Sends the file or message
            send(commands[1])
        elif commands[0] == 'disconnect':
            #Diconnect Function
            disconnect()
        elif commands[0] == 'show-status':
            #Prints Status()
            showStatus()
            pass
        elif commands[0] == 'show-log':
            #Prints Timed Log
            showLog()
            pass
        else:
            print("Invalid Command")

if __name__ == '__main__':
    main()