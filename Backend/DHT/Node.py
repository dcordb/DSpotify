import Pyro4
import random
import sys
import argparse
from Backend.DHT.Utils import Utils, get_alive_nodes, get_unused_port
from Backend.DHT.Settings import *
from Backend.DHT.NetworkWorker import get_songs_set

Pyro4.config.SERIALIZER = "pickle"
Pyro4.config.SERIALIZERS_ACCEPTED.add("pickle")
sys.excepthook = Pyro4.util.excepthook


@Pyro4.expose
@Pyro4.behavior(instance_mode="single")
class Node:
    def __init__(self, ip, port = 0, hash = None):
        # ip and port of node
        self._ip = ip
        self._port = port

        if self._port == 0:
            self._port = get_unused_port()

        # node DHT data
        self._finger = [None] * LOG_LEN
        self._predecessor = None
        self._successor_list = []

        # song list of node self
        self._songs = set()

        # port of the socket that is running on the node
        self.port_socket = None

        # is node added to DHT
        self._added = False

        # hash of node
        self._hash = hash

        if hash is None:
            self._hash = Utils.get_hash(ip + ":" + port)

        # logger of the node
        self.logger = Utils.init_logger("Node h=%d Log" % self._hash)

    ##############################################
    
    @property
    def ip(self):
        return self._ip

    @ip.setter
    def ip(self, ip):
        self._ip = ip

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, port):
        self._port = port
        
    ##############################################

    @property
    def finger(self):
        return self._finger

    @finger.setter
    def finger(self, finger):
        self._finger = finger

    @property
    def predecessor(self):
        return self._predecessor

    @predecessor.setter
    def predecessor(self, predecessor):
        self._predecessor = predecessor

    @property
    def successor_list(self):
        return self._successor_list

    @successor_list.setter
    def successor_list(self, successor_list):
        self._successor_list = successor_list

    ##############################################

    @property
    def songs(self):
        return self._songs

    @songs.setter
    def songs(self, songs):
        self._songs = songs

    ##############################################

    @property
    def port_socket(self):
        return self._port_socket

    @port_socket.setter
    def port_socket(self, port_socket):
        self._port_socket = port_socket

    ##############################################

    @property
    def added(self):
        return self._added

    @added.setter
    def added(self, added):
        self._added = added

    ##############################################
    
    @property
    def hash(self):
        return self._hash

    @hash.setter
    def hash(self, h):
        self._hash = h

    ##############################################

    def load_local_songs(self):
        return get_songs_set()

    def is_song_available(self, song_name):
        for song in self.songs:
            if song.name == song_name:
                return True

        return False

    def set_succesor_as_self(self):
        # this is a proxy of myself
        self.finger[0] = Pyro4.Proxy("PYRONAME:Node:" + str(self.hash))

    def ping(self):
        """
        Is node self alive
        :return: bool
        """
        return True

    def id(self, off: int = 0) -> int:
        """
        Returns id of a self + some offset off
        :param off: offset to add
        :return: int
        """
        return (self.hash + off) % SIZE

    def successor(self) -> Pyro4.Proxy:
        """
        Return successor of node self
        :return: [ Pyro4.Proxy | None ]
        """

        for other in [self.finger[0]] + self.successor_list:
            if other is None:
                continue

            if Utils.ping(other):
                self.finger[0] = other
                return other

        self.logger.error("No successor available :(")

    def find_successor(self, id: int):
        """
        Find successor of id
        :param id: identifier
        :return: Pyro4.Proxy
        """
        self.logger.info("Finding successor of id = %d" % id)

        if (self.predecessor is not None) and \
           Utils.ping(self.predecessor) and \
           Utils.between(id, self.predecessor.id(1), self.id(1)):
            return self

        node = self.find_predecessor(id)

        self.logger.info("Done")
        return node.successor()

    def find_predecessor(self, id: int):
        node = self

        if node.successor().id() == node.id():
            return node

        while not Utils.between(id, node.id(1), node.successor().id(1)):
            node = node.closest_preceding_finger(id)

        return node

    def closest_preceding_finger(self, id: int):
        """
        Returns closest preceding finger from id
        :param id: identifier
        :return: Pyro4.Proxy
        """
        for other in reversed(self.successor_list + self.finger):
            if (other is not None) and Utils.ping(other) and \
               Utils.between(other.id(), self.id(1), id):
                    return other

        return self

    def join(self, other: Pyro4.Proxy) -> None:
        """
        Join to DHT using node other
        :param other: node other
        :return: None
        """
        self.logger.info("Joined to DHT using node other (h = %d)" % other.id())

        self.finger[0] = other.find_successor(self.id())

    def stabilize(self) -> None:
        """
        Stabilize node self
        :return: None
        """
        self.logger.info("stabilizing...")

        succ = self.successor()

        if succ.id() != self.finger[0].id():
            self.finger[0] = succ

        x = succ.predecessor

        if (x is not None) and \
            Utils.ping(x) and \
            Utils.between(x.id(), self.id(1), succ.id()) and \
            self.id(1) != succ.id():
                self.finger[0] = x

        self.successor().notify(self)

    def notify(self, other) -> None:
        """
        Fixing predecessor
        :param other: other node
        :return: None
        """
        self.logger.info("notifying...")

        if self.predecessor is None or \
            not Utils.ping(self.predecessor) or \
            Utils.between(other.id(), self.predecessor.id(1), self.id()):
                self.predecessor = other

    def fix_fingers(self) -> None:
        """
        Fixing fingers of node self
        :return: None
        """
        self.logger.info("fixing fingers...")

        i = random.randint(1, LOG_LEN - 1)
        self.finger[i] = self.find_successor(self.id(1 << i))

    def update_successor_list(self) -> None:
        """
        Updates successor list of self
        :return: None
        """
        self.logger.info("updating successor list....")

        suc = self.successor()

        if suc.id() != self.id():
            successors = [suc]
            suc_list = suc.successor_list[:SUCC_LIST_LEN - 1]

            if suc_list and len(suc_list):
                successors += suc_list

            self.successor_list = successors


def register_node(cur_node):
    cur_node.logger.info("Registering node...")

    daemon = Pyro4.Daemon(cur_node.ip, cur_node.port)
    uri = daemon.register(cur_node)

    if cur_node.hash < 0 or cur_node.hash >= SIZE:
        cur_node.logger.error("Hash of node is not in range [0, SIZE). Exiting ...")
        exit(-1)

    alive = get_alive_nodes()

    for name, _uri in alive:
        proxy = Pyro4.Proxy(_uri)

        if Utils.ping(proxy):
            if proxy.hash == cur_node.hash:
                cur_node.logger.error("There exists other node with the same hash. Exiting ...")
                exit(-1)

    cur_node.logger.debug("Node location %s" % uri.location)

    with Pyro4.locateNS() as ns:
        ns.register("Node:" + str(cur_node.hash), uri)

    cur_node.set_succesor_as_self()

    cur_node.logger.info("Daemon Loop will run now ... Node is waiting for requests!")

    daemon.requestLoop()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Node creation script")
    parser.add_argument("--ip", default="127.0.0.1", type=str, help="IP address of a node, default is 127.0.0.1")
    parser.add_argument("--port", default=0, type=int, help="Port of node, default is 0 which means random port")
    parser.add_argument("--hash", default=None, type=int, help="Hash value of a node, default is None")
    args = parser.parse_args()

    cur_node = Node(args.ip, args.port, args.hash)

    register_node(cur_node)
