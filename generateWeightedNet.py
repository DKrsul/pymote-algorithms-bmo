from pymote.algorithms.KVM.PTConstruction import PTConstruction
from pymote.networkgenerator import NetworkGenerator
from pymote.npickle import write_pickle
from pymote.simulation import Simulation
from pymote.network import Network
import networkx as nx
import random

net_gen = NetworkGenerator(6)
net = net_gen.generate_random_network()

net.algorithms = (PTConstruction,)
net.show()

write_pickle(net, 'pt_mreza3.tar.gz')

sim = Simulation(net)
sim.run()

print "\n"
for node in net.nodes():
    print node.id, node.memory, node.status
    print " "
#sim.reset()

tmpPathList = []
resultCounter = 0
for node in net.nodes():
    for node2 in net.nodes():
        if not node == node2:
            tmpPathList = [p for p in nx.all_shortest_paths(net,source=node,target=node2, weight='weight')]
            shortestPath = node.memory['routingTable'][node2]
            for l in tmpPathList:
                l.remove(node)
            if shortestPath not in tmpPathList:
                resultCounter += 1

print "\nERRORS: " + str(resultCounter)
print "\nDone script."