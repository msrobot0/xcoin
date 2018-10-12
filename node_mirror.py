#Python file for running node
from coin import Ledger, Block, Transaction
import pickle
import hashlib
import helper
from twisted.internet.protocol import Factory, ClientFactory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, stdio
import json

#Import python ledger object, data type to be update to allow easier modifictaion
ledger = pickle.load( open( "ledger.p", "rb" ) )

#Enter address for node block rewards
my_address = int(input("Enter your address: "))

def nodeID(addr):
    """Helper function to create nodeid"""
    return addr.host + str(addr.port)

class NodeProtocol(LineReceiver):

    def __init__(self, addr, factory):
        self.state = "NEW"
        self.addr = addr
        self.factory = factory

    def connectionMade(self):
        self.state = "CONNECTED"
        #self.sendLine(b"connected")
        print("connected")

    def connectionLost(self, reason):
        self.state = "OLD"

    def lineReceived(self, line):
        message = pickle.loads(line)
        print("message_received")
        if message[0] == 0:
            self.factory.newBlock(message[1])

    def sendObject(self, data):
        message = pickle.dumps([0, data])
        self.sendLine(message)

class CommandProtocol(LineReceiver):
    delimiter = b'\n' # unix terminal style newlines. remove this line
                      # for use with Telnet

    def connectionMade(self):
        self.sendLine(b"Web checker console. Type 'help' for help.")

    def lineReceived(self, line):
        # Ignore blank lines
        if not line: return
        line = line.decode("ascii")

        # Parse the command
        commandParts = line.split()
        command = commandParts[0].lower()
        args = commandParts[1:]

        # Dispatch the command to the appropriate method.  Note that all you
        # need to do to implement a new command is add another do_* method.
        try:
            method = getattr(self, 'do_' + command)
        except AttributeError as e:
            self.sendLine(b'Error: no such command.')
        else:
            try:
                method(*args)
            except Exception as e:
                self.sendLine(b'Error: ' + str(e).encode("ascii"))

    def do_help(self, command=None):
        """help [command]: List commands, or show help on the given command"""
        if command:
            doc = getattr(self, 'do_' + command).__doc__
            self.sendLine(doc.encode("ascii"))
        else:
            commands = [cmd[3:].encode("ascii")
                        for cmd in dir(self)
                        if cmd.startswith('do_')]
            self.sendLine(b"Valid commands: " + b" ".join(commands))

    def do_quit(self):
        """quit: Quit this session"""
        self.sendLine(b'Goodbye.')
        self.transport.loseConnection()

    def do_balance(self, address):
        """Return balance of an address"""
        address = int(address)
        self.sendLine(b"Balance: " + str(factory.balance(address)).encode('UTF-8'))
        
    def do_send(self, value, addres):
        """check <url>: Attempt to download the given web page"""
        return

    def do_bootstrap(self):
        reactor.connectTCP("127.0.0.1", 8123, factory)

    def do_update(self):
        """ Create new block """
        factory.update()
        self.sendLine(b"New block created")

    def do_status(self):
        self.sendLine(str(ledger.block_num()).encode('UTF-8'))

    def __checkSuccess(self, pageData):
        msg = "Success: got {} bytes.".format(len(pageData))
        self.sendLine(msg.encode("ascii"))

    def __checkFailure(self, failure):
        msg = "Failure: " + failure.getErrorMessage()
        self.sendLine(msg.encode("ascii"))

    def connectionLost(self, reason):
        # stop the reactor, only because this is meant to be run in Stdio.
        reactor.stop()

class NodeFactory(ClientFactory):
    def __init__(self):
        self.new_transactions = []
        self.peers = {}

    def buildProtocol(self, addr):
        newProtocol = NodeProtocol(addr, self)
        self.peers[nodeID(addr)] = newProtocol
        return newProtocol

    def buildCommandProtocol(self):
        return CommandProtocol()

    def balance(self, address):
        return ledger.check_balance(address)

    def update(self):
        new_block = Block(self.new_transactions, 0, 0)
        if ledger.add(new_block):
            self.sendPeers(new_block)
        else:
            print("Invalid block")
        self.new_transactions = []

    def newBlock(self, block):
        if ledger.add(block):
            print("Received new block!")
        else:
            print("Invalid block")
        self.new_transactions = []
    
    def sendPeers(self, data):
        for peer in self.peers:
            self.peers[peer].sendObject(data)


        


factory = NodeFactory()
stdio.StandardIO(factory.buildCommandProtocol())
reactor.listenTCP(8124, factory)
reactor.run()