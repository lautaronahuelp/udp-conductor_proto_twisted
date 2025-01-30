from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol 
from socket import *
from copy import deepcopy

dispositivosRegistrados = {}


class Dispositivo(DatagramProtocol):
    def __init__(self, dispReg):
        self._dispReg = dispReg
      

    def datagramReceived(self, data, addr):
        #AAAA|R
        
        mensaje = data.decode("utf-8")
        mensajeSplit = mensaje.split("|")
        if mensajeSplit[1] == "R":
            if not(mensajeSplit[0] in self._dispReg):
                self._direccion = addr
                
                self._cuenta = mensajeSplit[0]
                self._dispReg[mensajeSplit[0]] = {
                                                    "cuenta": mensajeSplit[0],
                                                    "direccion": addr,
                                                }
                
                self.transport.write(("%s|R|OK" % mensajeSplit[0]).encode("utf-8"), addr)
                print(type(self.transport))
        if mensajeSplit[1] == "T":#tema unir con R
            
            if mensajeSplit[0] in self._dispReg:
                dispositivo = self._dispReg[mensajeSplit[0]]
                if dispositivo.getDireccion() != addr:
                    dispositivo.setDireccion(addr)#tema si llega mensaje falso
                self.transport.write(("%s|A" % mensajeSplit[0]).encode("utf-8"), addr)
        
        print(self._dispReg)
        

    def setDireccion(self, direccion):
        self._direccion = direccion

    def getDireccion(self):
        return self._direccion
    
    def enviarMensaje(self, mensaje, addr):
        self.transport.write(("SERV|M|%s" % mensaje).encode("utf-8"), addr)
        
    

class Servidor(DatagramProtocol):
    def __init__(self, dR, pD):
        self._dispReg = dR
        self._protoDisp = pD

    def datagramReceived(self, data, addr):
        #AAAA|M|MENSAJE
        mensaje = data.decode("utf-8")
        mensajeSplit = mensaje.split("|")
        if mensajeSplit[0] in self._dispReg:
            dispositivo = self._dispReg[mensajeSplit[0]]
            self._protoDisp.enviarMensaje(mensajeSplit[2], dispositivo["direccion"])
            self.transport.write("ENVIADO A DISPOSITIVO".encode("utf-8"), addr) #VER OPCIONES DE CALLBACK

        else:
            self.transport.write("DISPOSITIVO NO REGISTRADO".encode("utf-8"), addr)
        print(self._dispReg)


protoDisp = Dispositivo(dispositivosRegistrados)

reactor.listenUDP(9999, Servidor(dispositivosRegistrados, protoDisp))
reactor.listenUDP(3060, protoDisp)
reactor.run()