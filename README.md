# Dynamic Star Network

This is my final project for my Computer Networking I course. It is a way to reliably broadcast either ASCII strings or files to other nodes on the network. The network is also a self-organizing dynamic network, which means that the network reorganizes itself to make sending messages as quick as possible, and it has one central node.

## Running the Star-Node
To run the star-node, you must run this following command:

```python star-node.py <name> <local_port> <poc_address> <poc_port> <n>```

The arguments are as such:
* **name**: This is the name of the star-node. Must be an ASCII string between 1 and 16 characters long.
* **local_port**: The port number that this star-node is running on.
* **poc_address**: This is the address that the POC of this star-node is running at. If this star-node doesn't have a POC, set it to 0.
* **poc_port**: This is the port number that the POC of this star-node is running at. If this star-node doesn't have a POC, set it to 0.
* **n**: This is the maximum number of star-nodes in this network.
