from pymote.algorithm import NodeAlgorithm
from pymote.message import Message
import random


class PTConstruction(NodeAlgorithm):

    default_params =    {'neighborsKey': 'Neighbors', 'sourceKey': 'source', 'myDistanceKey': 'myDistance', 'ackCountKey': 'ackCount', 
                        'iterationKey': 'iteration', 'pathLengthKey': 'pathLength', 'childrenKey': 'children', 'unvisitedKey': 'unvisited',
                        'parentKey': 'parent', 'childCoundKey': 'childCount', 'neighborsMatrixKey': 'neighborsMatrix', 'firstIdKey': 'firstId'}


    def initializer(self):
        neighborsMatrix = [[0 for i in self.network.nodes()] for j in self.network.nodes()]
        
        firstId = self.network.nodes()[0].id

        ini_node = self.network.nodes()[0]

        for node in self.network.nodes():
            new = []
            node.memory[self.neighborsKey] = \
                node.compositeSensor.read()['Neighbors']

            for neighbour in node.memory[self.neighborsKey]:
                if neighborsMatrix[node.id-firstId][neighbour.id-firstId]==0 or neighborsMatrix[neighbour.id-firstId][node.id-firstId]==0:
                    dist = random.randint(1,20)
                    neighborsMatrix[node.id-firstId][neighbour.id-firstId] = dist
                    neighborsMatrix[neighbour.id-firstId][node.id-firstId] = dist
            node.memory[self.neighborsMatrixKey]=neighborsMatrix
            node.memory[self.firstIdKey] = firstId
            node.memory[self.iterationKey] = None
 
            node.status = 'IDLE'

        ini_node.status = 'INITIATOR'

        for i in neighborsMatrix:
            print i
             
        self.network.outbox.insert(0, Message(header=NodeAlgorithm.INI,
                                                 destination=ini_node))

    def initiator(self, node, message):
        if message.header == NodeAlgorithm.INI:
            node.memory[self.sourceKey] = True
            node.memory[self.myDistanceKey] = 0
            node.memory[self.ackCountKey] = len(node.memory[self.neighborsKey])
            node.send(Message(header='Notify',
                                                 destination=node.memory[self.neighborsKey]))

        elif (message.header == 'Ack'):
            node.memory[self.ackCountKey] -= 1
            if node.memory[self.ackCountKey] == 0:
                node.memory[self.iterationKey] = 1
            neighbourDistFull = node.memory[self.neighborsMatrixKey][node.id - node.memory[self.firstIdKey]]
            #print neighbourDistFull
            neighbourDist = [x for x in neighbourDistFull if x != 0]
            v = min(neighbourDist)
            node.memory[self.pathLengthKey] = v
            for neighbour in node.memory[self.neighborsKey]:
                if neighbour.id == neighbourDistFull.index(v)+node.memory[self.firstIdKey]:
                    node.memory[self.childrenKey] =neighbour

            node.send(Message(header='Expand',
                                                 destination=node.memory[self.childrenKey],
                                                 data=[node.memory[self.iterationKey], node.memory[self.pathLengthKey]]))

            unvisited = node.memory[self.neighborsKey]
            unvisited = unvisited.remove(node.memory[self.childrenKey])
            node.memory[self.unvisitedKey] = unvisited
            node.status = 'ACTIVE'


    def idle(self, node, message):
        if message.header == 'Notify':
            unvisited = node.memory[self.neighborsKey]
            unvisited = unvisited.remove(message.source)
            node.memory[self.unvisitedKey] = unvisited

            node.send(Message(header='Ack',
                                                 destination=message.source))
            node.status = 'AWAKE'



    def active(self, message, node):
        pass

    def awake(self, message, node):
        pass

    STATUS = {
        'INITIATOR': initiator,
        'IDLE': idle,
        'ACTIVE': active,
        'AWAKE': awake,
        #'WAITING_FOR_ACK': waitingForAck,
        #'COMPUTING': computing,
        #'DONE': done
    }