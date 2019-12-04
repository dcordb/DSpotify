from timeloop import Timeloop
from datetime import timedelta
import Pyro4
from Pyro4.errors import *
import argparse
from Backend.DHT.Utils import Utils

parser = argparse.ArgumentParser(description="Network Worker")
parser.add_argument("--st_time", default=1, type=int, help="How often stabilize each node, default 1s")
parser.add_argument("--ft_time", default=1, type=int, help="How often fix finger table indexes, default 1s")
parser.add_argument("--status_time", default=5, type=int, help="How often fix finger table indexes, default 5s")
args = parser.parse_args()


def get_alive_nodes():
    ns = Pyro4.locateNS()
    return list(ns.list(prefix="Node:").items())


def run_jobs():
    tl = Timeloop()

    @tl.job(timedelta(seconds=args.st_time))
    def stabilize():
        logger.info("Stabilizing all nodes...")

        alive = get_alive_nodes()

        for name, uri in alive:
            logger.debug("Stabilizing node %s..." % name)

            try:
                cur_node = Pyro4.Proxy(uri)
                cur_node.stabilize()
                logger.debug("Done stabilize node h = %d" % cur_node.hash)

            except CommunicationError:
                logger.error("It seems there have been some errors")

        logger.info("Done stabilizing nodes")

    @tl.job(timedelta(seconds=args.ft_time))
    def fix_fingers():
        logger.info("Fixing fingers...")

        alive = get_alive_nodes()

        for name, uri in alive:
            logger.debug("Fixing node %s..." % name)

            try:
                cur_node = Pyro4.Proxy(uri)
                cur_node.fix_to()
                logger.debug("Done fix fingers node h = %d" % cur_node.hash)

            except CommunicationError:
                logger.error("It seems there have been some errors")

        logger.info("Done fixing fingers")

    @tl.job(timedelta(seconds=args.status_time))
    def show_current_status():
        # this is for debugging purposes
        alive = get_alive_nodes()

        for name, uri in alive:
            try:
                cur_node = Pyro4.Proxy(uri)
                logger.debug(Utils.debug_node(cur_node))

            except CommunicationError:
                logger.error("It seems there have been some errors")

    logger.info("Running jobs of stabilize and fix fingers...")
    tl.start(block=True)


if __name__ == "__main__":
    logger = Utils.init_logger("Network Worker Logger")
    logger.info("Network Worker Initialized")
    logger.info("Stabilize frequency = %d, Fix fingers frequency = %d, Status Refreshing time = %d"
                % (args.st_time, args.ft_time, args.status_time))

    run_jobs()