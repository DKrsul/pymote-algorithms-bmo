from pymote.algorithm import NodeAlgorithm
from pymote.message import Message
import random
import math
import sys


class PTConstruction(NodeAlgorithm):

    messageCounter = 0
    default_params =    {'neighborsKey': 'Neighbors', 'sourceKey': 'source', 'myDistanceKey': 'myDistance', 'ackCountKey': 'ackCount', 
                        'iterationKey': 'iteration', 'pathLengthKey': 'pathLength', 'childrenKey': 'children', 'unvisitedKey': 'unvisited',
                        'parentKey': 'parent', 'childCountKey': 'childCount', 'weightKey':'weight', 'minPathKey': 'minPath', 'exitKey': 'exit',
                        'myChoiceKey': 'myChoice', 'routingTableKey': 'routingTable', 'masterKey': 'master', 'masterChildrenKey': 'masterChildren',
                        'tokenNeighboursKey': 'tokenNeighbours', 'macroIterationKey': 'macroIteration', 'parentMasterKey': 'parentMaster'}

    def initializer(self):
        #inicijalizacija polja za upis tezine brida za svaki cvor
        for u,v,w in self.network.edges(data=True):
            u.memory[self.weightKey] = dict()
            v.memory[self.weightKey] = dict()
        
        #dodavanje tezina svakom cvoru
        for u,v,w in self.network.edges(data=True):
            w = random.randint(1,10)
            u.memory[self.weightKey][v] = w
            v.memory[self.weightKey][u] = w

        #inicijalizacija svih cvorova u mrezi
        for node in self.network.nodes():
            #svakom cvoru postavi susjede
            node.memory[self.neighborsKey] = \
                node.compositeSensor.read()['Neighbors']

            #upisivanje tezina u net.adj radi testiranja
            for n in node.memory[self.neighborsKey]:
                self.network.adj[node].update({n:{'weight': node.memory[self.weightKey][n]}})

            #inicijalizacija varijabli za prvu (makro) iteraciju    
            self.initializeVariables(node, False)
            
            #postavi svaki cvor u IDLE stanje
            node.status = 'IDLE'

        #prvi cvor u mrezi postavi u status INITIATOR
        ini_node = self.network.nodes()[0]
        ini_node.status = 'INITIATOR'
        #prvi initiator postaje master
        ini_node.memory[self.masterKey] = True
        
        #slanje spontanog impulsa
        self.network.outbox.insert(0, Message(header=NodeAlgorithm.INI,
                                                 destination=ini_node))

    def initiator(self, node, message):
        if message.header == NodeAlgorithm.INI:
            #brojac poruka (za testiranje slozenosti)
            self.messageCounter += 1

            #svaki initiator mora postaviti defautne vrijednosti
            node.memory[self.sourceKey] = True      
            node.memory[self.myDistanceKey] = 0
            node.memory[self.ackCountKey] = len(node.memory[self.neighborsKey])

            #slanje notify poruke svim susjedima
            node.send(Message(header='Notify',
                              destination=node.memory[self.neighborsKey],
                              data=node.memory[self.macroIterationKey]))

        elif (message.header == 'Ack'):
            #brojac poruka (za testiranje slozenosti)
            self.messageCounter += 1

            #brojac za ack poruke
            node.memory[self.ackCountKey] -= 1

            #ako su primnjene ack poruke od svih susjeda, brojac je 0
            if node.memory[self.ackCountKey] == 0:
                node.memory[self.iterationKey] = 1
                #odaberi najblizeg susjeda
                minNeighbour = min(node.memory[self.weightKey], key=(lambda k: node.memory[self.weightKey][k]))
                v = node.memory[self.weightKey][minNeighbour]
                node.memory[self.pathLengthKey] = v
                #najblizeg susjeda dodaj u listu djece
                childrenList = list(node.memory[self.childrenKey])
                childrenList.append(minNeighbour)   
                node.memory[self.childrenKey] = childrenList
                #najblizem susjedu posalji Expand poruku       
                node.send(Message(header='Expand',
                                  destination=node.memory[self.childrenKey],
                                  data=[node.memory[self.iterationKey], node.memory[self.pathLengthKey]]))

                #najblizeg susjeda izbaci iz unvisited liste
                unvisited = list(node.memory[self.neighborsKey])
                for child in node.memory[self.childrenKey]:
                    unvisited.remove(child)

                node.memory[self.unvisitedKey] = unvisited
                node.status = 'ACTIVE'

    def idle(self, node, message):
        if message.header == 'Notify':
            self.messageCounter += 1
            self.processNotify(node, message, True)
            node.status = 'AWAKE'

        elif message.header == 'Token':
            self.messageCounter += 1
            #spremi informaciju o broju makroiteracije
            node.memory[self.macroIterationKey] = message.data
            #ako vec imas routing table
            if node.memory[self.routingTableKey]:
                #provjera ako postoji dijete kojemu jos nisi poslao token
                if node.memory[self.tokenNeighboursKey]:
                    tokenNeighbour = node.memory[self.tokenNeighboursKey][0]
                    node.memory[self.macroIterationKey] +=1
                    #slanje tokena dijetetu kojemu jos nije poslan
                    node.send(Message(header='Token',
                                 destination = tokenNeighbour,
                                 data=node.memory[self.macroIterationKey]))
                    #makni iz liste dijete kojemu si poslao token 
                    tokenNeighbours = list(node.memory[self.tokenNeighboursKey])
                    tokenNeighbours.remove(tokenNeighbour)
                    node.memory[self.tokenNeighboursKey] = tokenNeighbours

                else:
                    #ako si poslao svoj djeci token i nisi master salji token roditelju
                    if not node.memory[self.masterKey]:
                        node.send(Message(header='Token',
                                     destination = node.memory[self.parentMasterKey],
                                     data=node.memory[self.macroIterationKey]))
                    #ako si master i poslao si svoj djeci, algoritam je gotov i broadcasta se poruka o zavrsetku algoritma
                    else:
                        node.send(Message(header='Done',
                                 destination = node.memory[self.masterChildrenKey]))
                        node.status = 'DONE'

            #ako nemas routing table postani iniciator i pokreni novu makroiteraciju
            else:
                node.send(Message(header=NodeAlgorithm.INI,
                              destination=node))

                node.status = 'INITIATOR'

        #ako si primio header Done javi svojoj djeci da je algoritam zavrsen i postani DONE
        elif message.header == 'Done':
            self.messageCounter += 1

            node.send(Message(header='Done',
                             destination = node.memory[self.masterChildrenKey]))
            node.status = 'DONE'

            print self.messageCounter

    def active(self, node, message):
        if message.header == 'IterationCompleted':
            self.messageCounter += 1

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
            self.messageCounter += 1

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
            self.messageCounter += 1

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
            self.messageCounter += 1
            self.processNotify(node, message)

        elif message.header == 'Terminate':
            self.messageCounter += 1

            node.send(Message(header='Terminate',
                              destination =node.memory[self.childrenKey]))

            self.initializeVariables(node)
            node.status = 'IDLE'


    def awake(self, node, message):
        if message.header == 'Expand':
            self.messageCounter += 1

            node.memory[self.myDistanceKey] = message.data[1]
            node.memory[self.parentKey] = message.source
            node.memory[self.childrenKey] = []
            if len(node.memory[self.neighborsKey])>1:
                destination = list(node.memory[self.neighborsKey])
                destination.remove(message.source)
                node.send(Message(header='Notify',
                                  destination=destination,
                                  data=node.memory[self.macroIterationKey]))
                node.memory[self.ackCountKey] = len(node.memory[self.neighborsKey])-1
                node.status = 'WAITING_FOR_ACK'

            else:
                routingList = [node]
                node.send(Message(header='IterationCompleted',
                                  destination = node.memory[self.parentKey],
                                  data = routingList))
                node.status = 'ACTIVE'

        elif message.header == 'Notify':
            self.messageCounter += 1
            self.processNotify(node, message)


    def waitingForAck(self, node, message):
        if message.header == 'Ack':
            self.messageCounter += 1

            node.memory[self.ackCountKey] -=1
            if node.memory[self.ackCountKey] == 0:
                routingList = [node]
                node.send(Message(header='IterationCompleted',
                                    destination = node.memory[self.parentKey],
                                    data=routingList))
                node.status = 'ACTIVE'


    def computing(self, node, message):
        if message.header == 'MinValue':
            self.messageCounter += 1

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
            
            self.initializeVariables(node)

            if node.memory[self.tokenNeighboursKey]:
                tokenNeighbour = node.memory[self.tokenNeighboursKey][0]
                node.memory[self.macroIterationKey] +=1
                node.send(Message(header='Token',
                             destination = tokenNeighbour,
                             data=node.memory[self.macroIterationKey]))
                tokenNeighbours = list(node.memory[self.tokenNeighboursKey])
                tokenNeighbours.remove(tokenNeighbour)
                node.memory[self.tokenNeighboursKey] = tokenNeighbours

            else:
                if not node.memory[self.masterKey]:
                    node.send(Message(header='Token',
                                 destination = node.memory[self.parentMasterKey],
                                 data=node.memory[self.macroIterationKey]))

            node.status = 'IDLE'
        
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


    def initializeVariables(self, node, macro=True):

        if macro:
            if node.memory[self.macroIterationKey] == 0:
                node.memory[self.masterChildrenKey] = node.memory[self.childrenKey]
                node.memory[self.tokenNeighboursKey] = node.memory[self.childrenKey]
                node.memory[self.parentMasterKey] = node.memory[self.parentKey]
        else:
            node.memory[self.masterKey] = False
            node.memory[self.routingTableKey] = dict()
            node.memory[self.masterChildrenKey] = []
            node.memory[self.tokenNeighboursKey] = []
            node.memory[self.macroIterationKey] = 0
            node.memory[self.parentMasterKey] = None

        node.memory[self.childrenKey] = []
        node.memory[self.exitKey] = None
        node.memory[self.myChoiceKey] = None
        node.memory[self.minPathKey] = float('inf')
        node.memory[self.unvisitedKey] = []
        node.memory[self.myDistanceKey] = None
        node.memory[self.pathLengthKey] = None
        node.memory[self.childCountKey] = None
        node.memory[self.sourceKey] = False
        node.memory[self.parentKey] = None

    def processNotify(self, node, message, idle=False):
        node.memory[self.macroIterationKey] = message.data
        if not idle:
            unvisited = list(node.memory[self.unvisitedKey])
        else:
            unvisited = list(node.memory[self.neighborsKey])
        unvisited.remove(message.source)
        node.memory[self.unvisitedKey] = unvisited
        node.send(Message(header='Ack',
                          destination = message.source))


    STATUS = {
        'INITIATOR': initiator,
        'IDLE': idle,
        'ACTIVE': active,
        'AWAKE': awake,
        'WAITING_FOR_ACK': waitingForAck,
        'COMPUTING': computing,
        'DONE': done
    }