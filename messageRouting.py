from pymote.algorithms.KVM.PTConstruction import PTConstruction
from pymote.networkgenerator import NetworkGenerator
from pymote.network import Network
from pymote.simulation import Simulation

from pymote.npickle import write_pickle

net_gen = NetworkGenerator(7)

net = net_gen.generate_random_network()

#NAPOMENA: u saturated makla random initiatore
net.algorithms = (PTConstruction,)
#net.nodes()[0].memory['I'] = "Koja je tvoja temperatura?"

net.show()

#write_pickle(net, 'PTConstruction_mreza.tar.gz')

sim = Simulation(net)
sim.run()

for node in net.nodes():
    print "\n"
    print node.id, node.memory, node.status

#sim.reset()    
print "\nDone script."