# DSpotify

# To run the Chord implementation:
-Install the dependencies in requirements.txt

-First of all start Pyro4 name server, you do this from a terminal by typing pyro4-ns

-Use StartNode.py script to start a Node (DHT will be running with parameters LEN number of bits)
this can be found in the Node class. You use the script the following way open a terminal and go to
the root of the project folder, then execute:
    python3 -m Backend.DHT.StartNode --hash HASHCODE

This will run a node with hash equal to HASHCODE remember HASHCODE must be less than 2 ** LEN and
greater or equal than 0.

For each new node you want to execute doit in a new terminal.

After this in another terminal execute the NetworkWorker.py script, it runs the stabilize and
fix fingers jobs, also shows a detailed output.

Example:

you will have 6 terminals:

1 - this will be for the name server, just type pyro4-ns
2 - python3 -m Backend.DHT.StartNode --hash 0
3 - python3 -m Backend.DHT.StartNode --hash 1
4 - python3 -m Backend.DHT.StartNode --hash 3
5 - python3 -m Backend.DHT.StartNode --hash 6
6 - python3 -m Backend.DHT.NetworkWorker

You can also add new nodes it will work.

Each script has a --help option try it!

TODO: support node failures