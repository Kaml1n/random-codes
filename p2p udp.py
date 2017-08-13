#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os
import socket
import json
import hashlib
from threading import Event, Thread
from _socket import SOCK_DGRAM

PY3 = False
if sys.version_info.major == 3:
    PY3 = True

class Receiver(Thread):
    def __init__(self, s, the_end, p2pchat):
        super(Receiver, self).__init__()
        self.s = s
        self.the_end = the_end
        self.p2pchat = p2pchat
        

    def run(self):
        while not self.the_end.is_set():
            try:
                packet, addr = self.s.recvfrom(0xffff)  # Maksymalna wielkość pakietu UDP/IPv4.
                if PY3:
                    packet = str(packet, 'utf-8')
                packet = json.loads(packet)
                t = packet["type"]
                
            except socket.timeout:
                continue
            except ValueError:
                continue
            except KeyError:
                continue
            except TypeError:
                continue
            addr = "%s:%u" % addr
            self.p2pchat.handle_incoming(t, packet, addr)
        self.s.close()
                    

class P2PChat():
    def __init__(self):
        self.nickname = ''
        self.s = None
        self.the_end = Event()
        self.nearby_users = set()
        self.known_messages = set()
        self.id_counter = 0
        self.unique_tag = os.urandom(16)
    
    def main(self):
        if len(sys.argv) != 3:
            print("Usage: udpchat.py <port> <nick>")
            return
        
        port = int(sys.argv[1])
        self.nickname = sys.argv[2].strip()
        
        print("Creating p2p connection at port %u." % port)
        self.s = socket.socket(socket.AF_INET, SOCK_DGRAM)
        self.s.settimeout(0.2)
        self.s.bind(("0.0.0.0", port)) 
        
        th = Receiver(self.s, self.the_end, self)
        th.start()  
        
        print("Program started. Usage:\n"
              "    /add <domain or ip adress>:<port> - to add user\n"
              "    /exit - to exit\n"
              "    or wait for connection from another user...")
        
        try:
            while not self.the_end.is_set():
                sys.stdout.write("-> ")
                sys.stdout.flush()
                
                ln = sys.stdin.readline()
                if not ln:
                    self.the_end.set()
                    continue
                ln = ln.strip()
                if not ln:
                    continue
                
                if ln[0] == '/':
                    cmd = [l for l in ln.split(' ') if len(l) > 0]
                    self.handle_cmd(cmd[0], cmd[1:])
                else:
                    self.send_message(ln)
                    pass
        except KeyboardInterrupt:
            self.the_end.set()
        
        print("Bye!")
    
    def handle_cmd(self, cmd, args):
        if cmd == "/exit":
            self.the_end.set()
            return  
        if cmd == "/add":
            for p in args:
                try:
                    addr, port = p.split(':',1)
                    port = int(port)
                    addr = socket.gethostbyname(addr)
                except ValueError:
                    print("# Invalid address")
                    continue
                except socket.gaierror:
                    print("# Host not found")
                    continue
                addr = "%s:%u" % (addr, port)
                self.add_nearby_user(addr)
            return
        print("Unknown command.")
        
    def add_nearby_user(self, addr):
        if addr in self.nearby_users:
            return
        self.nearby_users.add(addr)
        self.send_packet({
            "type" : "HELLO",
            "name" : self.nickname
            }, addr)
        
    def handle_incoming(self, t, packet, addr):
        if t == "HELLO":
            print("# %s/%s connected" % (addr, packet["name"]))
            self.add_nearby_user(addr)
            return
        
        if t == "MESSAGE":
            self.add_nearby_user(addr)
            if packet["id"] in self.known_messages:
                return
            self.known_messages.add(packet["id"])
            packet["peers"].append(addr)
            print("\n[sent by: %s]" % '-->'.join(packet["peers"]))
            print("<%s> %s" % (packet["name"], packet["text"]))
            self.send_packet(packet, None, addr)
        
    def send_message(self, msg):
        hbase = "%s\0%s\0%u\0" % (self.nickname, msg, self.id_counter)
        self.id_counter += 1
        if PY3:
            hbase = bytes(hbase, 'utf-8')
        h = hashlib.md5(hbase + self.unique_tag).hexdigest()
        
        self.send_packet({
            "type": "MESSAGE",
            "name": self.nickname,
            "text": msg,
            "id": h,
            "peers": []
            })
        
    def send_packet(self, packet, target=None, excelude=set()):
        packet = json.dumps(packet)
        if PY3:
            packet = bytes(packet, 'utf-8')
        
        if not target:
            target = list(self.nearby_users)
        else:
            target = [target] 
        
        for t in target:
            if t in excelude:
                continue
            addr, port = t.split(":")
            port = int(port)
            self.s.sendto(packet, (addr, port))

if __name__ == '__main__':
    p2p = P2PChat().main()