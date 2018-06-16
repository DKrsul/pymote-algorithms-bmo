from pymote.algorithm import NodeAlgorithm
from pymote.message import Message
import random
import math
import sys


class MinHopRouting(NodeAlgorithm):

    default_params = {'neighborsKey': 'Neighbors', 'sourceKey': 'source', 'myDistanceKey': 'myDistance', 'ackCountKey': 'ackCount', 
                      'iterationKey': 'iteration', 'childrenKey': 'children', 'activeChildrenKey': 'activeChildren', 'unvisitedKey': 'unvisited',
                      'parentKey': 'parent', 'iterationCompletedCounterKey':'iterationCompletedCounter', 'terminateCouterKey': 'terminateCouter',
                      'routingTableKey': 'routingTable', 'routingListKey': 'routingList', 'masterKey': 'master', 'macroIterationKey': 'macroIteration',
                      'masterChildrenKey': 'masterChildren', 'masterParentKey': 'masterParent', 'tokenNeighboursKey': 'tokenNeighbours'}


    def initializer(self):
        ini_node = self.network.nodes()[0]

        for node in self.network.nodes():
            node.memory[self.neighborsKey] = \
                node.compositeSensor.read()['Neighbors']
            node.memory[self.sourceKey] = False
            node.memory[self.masterKey] = False
            node.memory[self.myDistanceKey] = 0
            node.memory[self.childrenKey] = []
            node.memory[self.masterChildrenKey] = []
            node.memory[self.parentKey] = None
            node.memory[self.masterParentKey] = None
            node.memory[self.activeChildrenKey] = []
            node.memory[self.iterationCompletedCounterKey] = 0
            node.memory[self.terminateCouterKey] = 0
            node.memory[self.macroIterationKey] = -1
            node.memory[self.unvisitedKey] = []
            node.memory[self.tokenNeighboursKey] = []
            node.memory[self.routingTableKey] = dict()
            node.memory[self.routingListKey] = []
            node.memory[self.ackCountKey] = 0
            node.status = 'IDLE'

        ini_node.status = 'INITIATOR'
        ini_node.memory[self.masterKey] = True
        ini_node.memory[self.macroIterationKey] = 0

        self.network.outbox.insert(0, Message(header=NodeAlgorithm.INI,destination=ini_node))


    def initiator(self, node, message):
        if message.header == NodeAlgorithm.INI:
            node.memory[self.sourceKey] = True
            node.memory[self.unvisitedKey] = node.memory[self.neighborsKey]
            node.memory[self.ackCountKey] = len(node.memory[self.neighborsKey])
            node.send(Message(header='Explore',
                              data=[1, node.memory[self.macroIterationKey]],
                              destination=node.memory[self.neighborsKey]))

        elif message.header == "Ack" and message.data[0] == 'Positive':
            #count received responses from neighbors
            node.memory[self.ackCountKey] -= 1

            #add initiator neighbors (i=1) to its childrend
            children = list(node.memory[self.childrenKey])
            children.append(message.source)
            node.memory[self.childrenKey] = children

            #add source to routing table
            node.memory[self.routingTableKey][message.source] = message.source

            #add initiator neighbors (i=1) to its activeChildrend (not done)
            activeChildren = list(node.memory[self.activeChildrenKey])
            activeChildren.append(message.source)
            node.memory[self.activeChildrenKey] = activeChildren

            #remove visited node from unvisited list
            unvisited = list(node.memory[self.unvisitedKey])
            unvisited.remove(message.source)
            node.memory[self.unvisitedKey] = unvisited

            #if all responses received start new iteration on new level (new distance)
            if (node.memory[self.ackCountKey] == 0):
                #send explore message to nodes on next iteration (distance)
                iteration = message.data[1] + 1
                node.send(Message(header='Start Iteration',
                                  data=iteration,
                                  destination=node.memory[self.childrenKey]))
                node.status = 'ACTIVE'


    def idle(self, node, message):

        if message.header == 'Explore':
            #initialize unvisited array for all nodes (except initiator)
            if node.memory[self.macroIterationKey] < message.data[1]:

                node.memory[self.unvisitedKey] = node.memory[self.neighborsKey]

                #save distance 
                node.memory[self.myDistanceKey] = message.data[0]

                #save macroiteration
                node.memory[self.macroIterationKey] = message.data[1]

                #mark sender as parent
                node.memory[self.parentKey] = message.source

                #remove visited node (source) from unvisited list
                unvisited = list(node.memory[self.unvisitedKey])
                unvisited.remove(message.source)
                node.memory[self.unvisitedKey] = unvisited

                #initialize ack counter for all nodes (except initiator)
                node.memory[self.ackCountKey] = len(unvisited)

                #send positive ack to parent
                node.send(Message(header='Ack',
                                 data=['Positive', message.data[0]],
                                 destination=node.memory[self.parentKey]))

                node.status = 'ACTIVE'

            else:
                node.send(Message(header='Ack',
                                 data=['Negative', message.data[0]],
                                 destination=message.source))


        elif message.header == 'Token':
            if not node.memory[self.routingTableKey]:
                node.memory[self.macroIterationKey] = message.data+1
                node.send(Message(header=NodeAlgorithm.INI,
                              destination=node))
                node.status = 'INITIATOR'

            else:
                if node.memory[self.tokenNeighboursKey]:
                    node.memory[self.macroIterationKey]+=1
                    tokenNeighbour = node.memory[self.tokenNeighboursKey][0]
                    node.send(Message(header='Token',
                                  data=node.memory[self.macroIterationKey],
                                  destination=tokenNeighbour))
                    tokenNeighbours = list(node.memory[self.tokenNeighboursKey])
                    tokenNeighbours.remove(tokenNeighbour)
                    node.memory[self.tokenNeighboursKey] = tokenNeighbours
                else:
                    if not node.memory[self.masterKey]:
                        node.send(Message(header='Token',
                                  data=node.memory[self.macroIterationKey],
                                  destination=node.memory[self.masterParentKey]))
                    else:
                        node.send(Message(header='Done',
                                  destination=node.memory[self.masterChildrenKey]))
                        node.status = "DONE"


        elif message.header == 'Done':
            node.send(Message(header='Done',
                             destination=node.memory[self.masterChildrenKey]))
            node.status = 'DONE'



    def active(self, node, message):
        if message.header == 'Ack':
            #postavljati ack counter na broj unvisited cvorova ??
            if message.data[0] == 'Positive':
                #count received responses from neighbors
                node.memory[self.ackCountKey] -= 1

                node.memory[self.routingListKey].append(message.source)

                #add initiator neighbors (i=1) to its childrend
                children = list(node.memory[self.childrenKey])
                children.append(message.source)
                node.memory[self.childrenKey] = children

                #add initiator neighbors (i=1) to its activeChildrend (not done)
                activeChildren = list(node.memory[self.activeChildrenKey])
                activeChildren.append(message.source)
                node.memory[self.activeChildrenKey] = activeChildren

                #remove visited node (source) from unvisited list
                unvisited = list(node.memory[self.unvisitedKey])
                unvisited.remove(message.source)
                node.memory[self.unvisitedKey] = unvisited

            else: #message.data[0] == 'Negative'
                #count received responses from neighbors
                node.memory[self.ackCountKey] -= 1

                #remove visited node (source) from unvisited list
                unvisited = list(node.memory[self.unvisitedKey])
                if message.source in unvisited:
                    unvisited.remove(message.source)
                    node.memory[self.unvisitedKey] = unvisited

            #initialize ack counter for all nodes (except initiator)
            #node.memory[self.ackCountKey] = len(unvisited)

            if node.memory[self.ackCountKey] == 0: 
                #send iteration completed to parent when new node is added to tree
                node.send(Message(header='Iteration Completed',
                                  data=[message.data[1], node.memory[self.routingListKey]], #proslijedi br iteracije (distance)
                                  destination=node.memory[self.parentKey]))


        if message.header == 'Iteration Completed':
            node.memory[self.iterationCompletedCounterKey] += 1
            activeChildren = list(node.memory[self.activeChildrenKey])
            if node.memory[self.sourceKey] and message.data[1]:
                for n in message.data[1]:
                        node.memory[self.routingTableKey][n] = message.source


            if node.memory[self.iterationCompletedCounterKey] == len(activeChildren):
                #reset counter
                node.memory[self.iterationCompletedCounterKey] = 0
                if not (node.memory[self.sourceKey]):
                    #send iteration completed to parent when new node is added to tree
                    node.send(Message(header='Iteration Completed',
                                      data=[message.data[0], message.data[1]], #proslijedi br iteracije (distance)
                                      destination=node.memory[self.parentKey]))

                else:
                    for n in message.data[1]:
                        node.memory[self.routingTableKey][n] = message.source

                    iteration = message.data[0] + 1 #povecaj br iteracije (distance)
                    node.send(Message(header='Start Iteration',
                                      data=iteration+1,
                                      destination=node.memory[self.activeChildrenKey]))
          
        if message.header == 'Start Iteration':
            unvisited = list(node.memory[self.unvisitedKey])
            activeChildren = list(node.memory[self.activeChildrenKey])
            node.memory[self.routingListKey] = []
        
            if ( ((node.memory[self.myDistanceKey] <= (message.data - 1)) and (node.memory[self.myDistanceKey] != 0) ) ):
                
                destination = node.memory[self.unvisitedKey]
                node.memory[self.ackCountKey] = len(destination)

                if destination:
                    #node.memory[self.ackCountKey] = len(unvisited)
                    node.send(Message(header='Explore',
                                      data=[message.data, node.memory[self.macroIterationKey]], 
                                      destination=destination))
                elif activeChildren:
                    node.send(Message(header='Start Iteration',
                                  data=message.data,
                                  destination=node.memory[self.activeChildrenKey]))
                else: #list zaprimio poruku
                    node.send(Message(header='Terminate',
                                  data=message.data,
                                  destination=node.memory[self.parentKey]))
                    
                    if node.memory[self.macroIterationKey] == 0:
                        node.memory[self.masterChildrenKey] = node.memory[self.childrenKey]
                        node.memory[self.masterParentKey] = node.memory[self.parentKey]
                        node.memory[self.tokenNeighboursKey] = node.memory[self.childrenKey]
                    node.memory[self.sourceKey] = False
                    node.memory[self.myDistanceKey] = 0
                    node.memory[self.childrenKey] = []
                    node.memory[self.parentKey] = None
                    node.memory[self.activeChildrenKey] = []
                    node.memory[self.iterationCompletedCounterKey] = 0
                    node.memory[self.terminateCouterKey] = 0
                    node.memory[self.unvisitedKey] = []
                    node.memory[self.routingListKey] = []
                    node.memory[self.ackCountKey] = 0

                    node.status = 'IDLE'

                    

            else:
                #set distance to message data
                node.memory[self.myDistanceKey] = message.data
                #set parent to message source
                node.memory[self.parentKey] = message.source

                #become part of the tree ??

                #send positive ack to parent
                node.send(Message(header='Ack',
                                  data=['Positive', message.data],
                                  destination=node.memory[self.parentKey]))



        if message.header == 'Explore':

            #if node distance is already calculated, he is already in tree
            if ( node.memory[self.myDistanceKey] != 0 ):
                #send negative ack to parent
                node.send(Message(header='Ack',
                                  data=['Negative', message.data[0]],
                                  destination=message.source))
            
            #if node not in tree (first next neighbor)
            else:
                #set distance to message data
                node.memory[self.myDistanceKey] = message.data[0]
                #set parent to message source
                node.memory[self.parentKey] = message.source

                #become part of the tree ??

                #send positive ack to parent
                node.send(Message(header='Ack',
                                  data=['Positive', message.data[0]],
                                  destination=node.memory[self.parentKey]))

        if message.header == 'Terminate':
            node.memory[self.terminateCouterKey] += 1

            #remove message sender from activeChildrend (not done)
            activeChildren = list(node.memory[self.activeChildrenKey])
            activeChildren.remove(message.source)
            node.memory[self.activeChildrenKey] = activeChildren

            if activeChildren and (node.memory[self.iterationCompletedCounterKey] == len(activeChildren)):
                #reset counter
                node.memory[self.iterationCompletedCounterKey] = 0
                
                if not node.memory[self.sourceKey]:
                    node.send(Message(header='Iteration Completed',
                                  data=[message.data, node.memory[self.routingListKey]], #proslijedi br iteracije (distance)
                                  destination=node.memory[self.parentKey]))
                else:
                    node.send(Message(header='Start Iteration',
                                  data=message.data, #proslijedi br iteracije (distance)
                                  destination=node.memory[self.activeChildrenKey]))                    

            children = list(node.memory[self.childrenKey])
            ##kad si dobio sve terminate
            if node.memory[self.terminateCouterKey] == len(children):
                #ako nisi source
                if not node.memory[self.sourceKey]:
                    node.send(Message(header='Terminate',
                                      data=message.data,
                                      destination=node.memory[self.parentKey]))

                    if node.memory[self.macroIterationKey] == 0:
                        node.memory[self.masterChildrenKey] = node.memory[self.childrenKey]
                        node.memory[self.masterParentKey] = node.memory[self.parentKey]
                        node.memory[self.tokenNeighboursKey] = node.memory[self.childrenKey]
                    node.memory[self.sourceKey] = False
                    node.memory[self.myDistanceKey] = 0
                    node.memory[self.childrenKey] = []
                    node.memory[self.parentKey] = None
                    node.memory[self.activeChildrenKey] = []
                    node.memory[self.iterationCompletedCounterKey] = 0
                    node.memory[self.terminateCouterKey] = 0
                    node.memory[self.unvisitedKey] = []
                    node.memory[self.routingListKey] = []
                    node.memory[self.ackCountKey] = 0

                    node.status = 'IDLE'
                #ako si source
                else:
                    if node.memory[self.macroIterationKey] == 0:
                        node.memory[self.masterChildrenKey] = node.memory[self.childrenKey]
                        node.memory[self.masterParentKey] = node.memory[self.parentKey]
                        node.memory[self.tokenNeighboursKey] = node.memory[self.childrenKey]
                    node.memory[self.sourceKey] = False
                    node.memory[self.myDistanceKey] = 0
                    node.memory[self.childrenKey] = []
                    node.memory[self.parentKey] = None
                    node.memory[self.activeChildrenKey] = []
                    node.memory[self.iterationCompletedCounterKey] = 0
                    node.memory[self.terminateCouterKey] = 0
                    node.memory[self.unvisitedKey] = []
                    node.memory[self.routingListKey] = []
                    node.memory[self.ackCountKey] = 0


                    if node.memory[self.tokenNeighboursKey]:
                        tokenNeighbour = node.memory[self.tokenNeighboursKey][0]
                        node.send(Message(header='Token',
                                      data=node.memory[self.macroIterationKey],
                                      destination=tokenNeighbour))
                        tokenNeighbours = list(node.memory[self.tokenNeighboursKey])
                        tokenNeighbours.remove(tokenNeighbour)
                        node.memory[self.tokenNeighboursKey] = tokenNeighbours
                        node.status = 'IDLE'

                    else:
                        if not node.memory[self.masterKey]:
                            node.send(Message(header='Token',
                                      data=node.memory[self.macroIterationKey],
                                      destination=node.memory[self.masterParentKey]))
                            node.status = 'IDLE'

                        else:
                            node.send(Message(header='Done',
                                      destination=node.memory[self.masterChildrenKey]))
                            node.status='DONE'



               


    def done(self, node, message):
        pass

    
    STATUS = {
        'INITIATOR': initiator,
        'IDLE': idle,
        'ACTIVE': active,
        'DONE': done
    }