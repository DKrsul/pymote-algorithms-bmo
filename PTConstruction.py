from pymote.algorithm import NodeAlgorithm
from pymote.message import Message
import random
import math
import sys


class PTConstruction(NodeAlgorithm):

    default_params =    {'neighborsKey': 'Neighbors', 'sourceKey': 'source', 'myDistanceKey': 'myDistance', 'ackCountKey': 'ackCount', 
                        'iterationKey': 'iteration', 'pathLengthKey': 'pathLength', 'childrenKey': 'children', 'unvisitedKey': 'unvisited',
                        'parentKey': 'parent', 'childCountKey': 'childCount', 'weightKey':'weight', 'minPathKey': 'minPath', 'exitKey': 'exit',
                        'myChoiceKey': 'myChoice', 'routingTableKey': 'routingTable'}


    def initializer(self):
        ini_node = self.network.nodes()[0]

        for u,v,w in self.network.edges(data=True):
            u.memory[self.weightKey] = dict()
            v.memory[self.weightKey] = dict()

        for u,v,w in self.network.edges(data=True):
            w = random.randint(0,10)
            u.memory[self.weightKey][v] = w
            v.memory[self.weightKey][u] = w

        for node in self.network.nodes():
            node.memory[self.neighborsKey] = \
                node.compositeSensor.read()['Neighbors']
            
            node.memory[self.childrenKey] = []
            node.memory[self.exitKey] = None
            node.memory[self.myChoiceKey] = None
            node.memory[self.sourceKey] = False
            node.memory[self.minPathKey] = float('inf')
            node.memory[self.routingTableKey] = dict()
 
            node.status = 'IDLE'

        ini_node.status = 'INITIATOR'
             
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
                minNeighbour = min(node.memory[self.weightKey], key=(lambda k: node.memory[self.weightKey][k]))
                v = node.memory[self.weightKey][minNeighbour]
                node.memory[self.pathLengthKey] = v
                childrenList = list(node.memory[self.childrenKey])
                childrenList.append(minNeighbour)   
                node.memory[self.childrenKey] = childrenList       
                node.send(Message(header='Expand',
                                  destination=node.memory[self.childrenKey],
                                  data=[node.memory[self.iterationKey], node.memory[self.pathLengthKey]]))

                unvisited = list(node.memory[self.neighborsKey])
                for child in node.memory[self.childrenKey]:
                    unvisited.remove(child)

                node.memory[self.unvisitedKey] = unvisited
                node.status = 'ACTIVE'


    def idle(self, node, message):
        if message.header == 'Notify':
            unvisited = list(node.memory[self.neighborsKey])
            unvisited.remove(message.source)
            node.memory[self.unvisitedKey] = unvisited
            node.send(Message(header='Ack',
                              destination=message.source))
            node.status = 'AWAKE'



    def active(self, node, message):
        if message.header == 'IterationCompleted':
            routingList=list(message.data)
            routingList.insert(0, node)
            if not(node.memory[self.sourceKey]):
                node.send(Message(header='IterationCompleted',
                                  destination = node.memory[self.parentKey],
                                  data = routingList))
            else:
                node.memory[self.routingTableKey][message.data[-1]] = message.data
                node.memory[self.iterationKey] +=1
                node.send(Message(header='StartIteration',
                                  destination = node.memory[self.childrenKey],
                                  data = node.memory[self.iterationKey]))
                self.computeLocalMinimum(node)
                node.memory[self.childCountKey] = 0
                node.status = 'COMPUTING'

        elif message.header == 'StartIteration':
            node.memory[self.iterationKey] = message.data
            self.computeLocalMinimum(node)
            if not node.memory[self.childrenKey]:
                node.send(Message(header='MinValue',
                                  destination = node.memory[self.parentKey],
                                  data = node.memory[self.minPathKey]))
            else:
                node.send(Message(header='StartIteration',
                                  destination = node.memory[self.childrenKey],
                                  data = node.memory[self.iterationKey]))
                node.memory[self.childCountKey] = 0
                node.status = 'COMPUTING'

        elif message.header == 'Expand':
            node.send(Message(header='Expand',
                              destination = node.memory[self.exitKey],
                              data = [message.data[0], message.data[1]]))
            
            if (node.memory[self.exitKey] == node.memory[self.myChoiceKey]) and (node.memory[self.myChoiceKey] != None):
                children = list(node.memory[self.childrenKey]) 
                if node.memory[self.myChoiceKey] not in children:
                    children.append(node.memory[self.myChoiceKey])
                    node.memory[self.childrenKey] = children
                if node.memory[self.unvisitedKey]:
                    unvisited = list(node.memory[self.unvisitedKey])
                    if node.memory[self.myChoiceKey] in unvisited:
                        unvisited.remove(node.memory[self.myChoiceKey])
                        node.memory[self.unvisitedKey] = unvisited

        elif message.header == 'Notify':
            unvisited = list(node.memory[self.unvisitedKey])
            unvisited.remove(message.source)
            node.memory[self.unvisitedKey] = unvisited
            node.send(Message(header='Ack',
                              destination = message.source))

        elif message.header == 'Terminate':
            node.send(Message(header='Terminate',
                              destination =node.memory[self.childrenKey]))
            node.status = 'DONE'


    def awake(self, node, message):
        if message.header == 'Expand':
            node.memory[self.myDistanceKey] = message.data[1]
            node.memory[self.parentKey] = message.source
            node.memory[self.childrenKey] = []
            if len(node.memory[self.neighborsKey])>1:
                destination = list(node.memory[self.neighborsKey])
                destination.remove(message.source)
                node.send(Message(header='Notify',
                                  destination=destination))
                node.memory[self.ackCountKey] = len(node.memory[self.neighborsKey])-1
                node.status = 'WAITING_FOR_ACK'

            else:
                routingList = [node]
                node.send(Message(header='IterationCompleted',
                                  destination = node.memory[self.parentKey],
                                  data = routingList))
                node.status = 'ACTIVE'

        elif message.header == 'Notify':
            unvisited = list(node.memory[self.unvisitedKey])
            unvisited.remove(message.source)
            node.memory[self.unvisitedKey] = unvisited
            node.send(Message(header='Ack',
                              destination= message.source))


    def waitingForAck(self, node, message):
        if message.header == 'Ack':
            node.memory[self.ackCountKey] -=1
            if node.memory[self.ackCountKey] == 0:
                routingList = [node]
                node.send(Message(header='IterationCompleted',
                                    destination = node.memory[self.parentKey],
                                    data=routingList))
                node.status = 'ACTIVE'


    def computing(self, node, message):
        if message.header == 'MinValue':
            if message.data < node.memory[self.minPathKey]: 
                node.memory[self.minPathKey] = message.data
                node.memory[self.exitKey] = message.source
            node.memory[self.childCountKey] +=1
            if node.memory[self.childCountKey] == len(node.memory[self.childrenKey]):
                if not(node.memory[self.sourceKey]):
                    node.send(Message(header='MinValue',
                                      destination = node.memory[self.parentKey],
                                      data = node.memory[self.minPathKey]))
                    node.status = 'ACTIVE'
                else:
                    self.checkForTermination(node)

    def done(self, node, message):
        pass

    def computeLocalMinimum(self, node):
        if not node.memory[self.unvisitedKey]:
            node.memory[self.minPathKey] = float("inf")
        else:
            minUnvisNeighbourNode = list(node.memory[self.unvisitedKey])[0]  
            minUnvisNeighbourValue = node.memory[self.weightKey][minUnvisNeighbourNode]
            for n in node.memory[self.unvisitedKey]:
                if node.memory[self.weightKey][n] < minUnvisNeighbourValue:
                    minUnvisNeighbourNode = n
                    minUnvisNeighbourValue = node.memory[self.weightKey][n]
            node.memory[self.minPathKey] = node.memory[self.myDistanceKey] + minUnvisNeighbourValue
            node.memory[self.myChoiceKey] = minUnvisNeighbourNode
            node.memory[self.exitKey] = minUnvisNeighbourNode


    def checkForTermination(self, node):
        if node.memory[self.minPathKey] == float("inf"):
            node.send(Message(header='Terminate',
                             destination = node.memory[self.childrenKey]))
            node.status = 'DONE'
        else:
            if (node.memory[self.exitKey] == node.memory[self.myChoiceKey]):
                children = list(node.memory[self.childrenKey])
                if node.memory[self.exitKey] not in children:
                    children.append(node.memory[self.exitKey])
                node.memory[self.childrenKey] = children

                unvisited = list(node.memory[self.unvisitedKey])
                if node.memory[self.exitKey] in unvisited:
                    unvisited.remove(node.memory[self.exitKey])
                node.memory[self.unvisitedKey] = unvisited

            node.send(Message(header='Expand',
                              destination = node.memory[self.exitKey],
                              data = [node.memory[self.iterationKey], node.memory[self.minPathKey]]))
            node.status = 'ACTIVE'




    STATUS = {
        'INITIATOR': initiator,
        'IDLE': idle,
        'ACTIVE': active,
        'AWAKE': awake,
        'WAITING_FOR_ACK': waitingForAck,
        'COMPUTING': computing,
        'DONE': done
    }