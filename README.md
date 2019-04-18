# CS 3251: Dynamic Star Network

Authors: Hemanth Chittanuru and Austin Cho

## Message Formats
* **RTT Calculation Request:** RTT Request from *name of node* at *sent time*
* **RTT Calculation Response:** RTT Response from *name of node* Sent Time: *original sent time*
* **POC Node Discovery:** POC Created: *Name of Node* has been created
* **POC Acknowledgment:** POC ACK from *Name of Node*
* **Other Node Discovery:** Node in network: *Name of node* *Node's address*
* **Node Discovery ACK:** Discovery ACK from *Name of node*
* **Disconnecting Node:** Disconnecting: *Name of node*
* **Message:** 1 Sender: *Name of node* Sent time *Message contents*
* **File:** 2 Sender: *Name of node* Sent time *File Name* *File contents*
* **Message Acknowledgment:** Message ACK from *Name of node*
* **File Acknowledgment:** File ACK from *Name of node*
* **RTT Sum:** RTT Sum from *Name of node* is: *RTT Value*
* **RTT Sum ACK:** Sum ACK from *Name of node*


## Running the Star-Node
To run the star-node, you must run this following command:

```python star-node.py <name> <local_port> <poc_address> <poc_port> <n>```

The arguments are as such:
* **name**: This is the name of the star-node. Must be an ASCII string between 1 and 16 characters long.
* **local_port**: The port number that this star-node is running on.
* **poc_address**: This is the address that the POC of this star-node is running at. If this star-node doesn't have a POC, set it to 0.
* **poc_port**: This is the port number that the POC of this star-node is running at. If this star-node doesn't have a POC, set it to 0.
* **n**: This is the maximum number of star-nodes in this network.# Dynamic-Star-Network
