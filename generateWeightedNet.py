from pymote.algorithms.KVM.PTConstruction import PTConstruction
from pymote.networkgenerator import NetworkGenerator
from pymote.npickle import write_pickle
from pymote.simulation import Simulation
from pymote.network import Network
import networkx as nx
import random

#G = nx.gnm_random_graph(5,5)
#net_gen = NetworkGenerator(5)
#net = net_gen.generate_random_network()
#net = Network()

net_gen = NetworkGenerator(7)
net = net_gen.generate_random_network()

"""
net.add_weighted_edges_from([(net.nodes()[0],net.nodes()[1],{'weight':0.6}), (net.nodes()[2],net.nodes()[1],{'weight':0.6}), (net.nodes()[0],net.nodes()[2],{'weight':0.6})])
net.add_weighted_edges_from([net.nodes()])

for u,v,d in net.edges(data=True):
    d['weight'] = random.randint(0,10)
    print u, v, d
    u.memory['weight'] = d['weight']
    v.memory['weight'] = d['weight']
"""

net.algorithms = (PTConstruction,)
net.show()

write_pickle(net, 'pt_mreza3.tar.gz')

sim = Simulation(net)
sim.run()

print "\n"
for node in net.nodes():
    print node.id, node.memory, node.status
#sim.reset()

print "\nDone script."