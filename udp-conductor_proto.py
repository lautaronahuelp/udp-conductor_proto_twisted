from twisted.internet import reactor
from twisted.internet.protocol import DatagramProtocol 
import datetime




class Dispositivo(DatagramProtocol):
    def __init__(self):
        self._dispReg = {} #DISPOSITIVOS REGISTRADOS
        self._regPend = {} #DISPOSITIVOS REGISTRADO QUE CAMBIARON DE DIRECCION
      

    def datagramReceived(self, data, addr):
        #AAAA|R
        
        mensaje = data.decode("utf-8")

        if mensaje == "@":#HB
            for item in self._dispReg:
                if(self._dispReg[item]["direccion"] == addr):
                    self._dispReg[item]["ultimo_contacto"] = datetime.datetime.now()
                    print(self._dispReg[item])
                    break
            
        else:
            mensajeSplit = mensaje.split("|")

            if mensajeSplit[1] == "R":#MENSAJE DE REGISTRO
                if not(mensajeSplit[0] in self._dispReg):
                    self._direccion = addr
                    
                    self._cuenta = mensajeSplit[0]
                    self._dispReg[mensajeSplit[0]] = {
                                                        "cuenta": mensajeSplit[0],
                                                        "direccion": addr,
                                                        "ultimo_contacto": datetime.datetime.now() 
                                                    }
                    
                    self.transport.write(("%s|R|OK" % mensajeSplit[0]).encode("utf-8"), addr)

            if mensajeSplit[1] == "T":#MENSAJE DE TEST
                
                if mensajeSplit[0] in self._dispReg:
                    dispositivo = self._dispReg[mensajeSplit[0]]
                    if dispositivo['direccion'] == addr:
                        dispositivo["ultimo_contacto"] = datetime.datetime.now()
                        self.transport.write(("%s|A" % mensajeSplit[0]).encode("utf-8"), addr)

                    else:
                        self._regPend[mensajeSplit[0]] = self._dispReg.pop(mensajeSplit[0])

                    
                    
        
        print(self._dispReg)
    
    def enviarMensaje(self, mensaje, cuenta):
        if cuenta in self._dispReg:
            self.transport.write(("SERV|M|%s" % mensaje).encode("utf-8"), self._dispReg[cuenta]["direccion"])
            return True
        else:
            return False

    def setDireccion(self, direccion):
        self._direccion = direccion

    def getDireccion(self):
        return self._direccion
    

class Servidor(DatagramProtocol):
    def __init__(self, pD):
        self._protoDisp = pD

    def datagramReceived(self, data, addr):
        #AAAA|M|MENSAJE
        mensaje = data.decode("utf-8")
        mensajeSplit = mensaje.split("|")
        
        if self._protoDisp.enviarMensaje(mensajeSplit[2], mensajeSplit[0]):
            self.transport.write("ENVIADO A DISPOSITIVO".encode("utf-8"), addr) #VER OPCIONES DE CALLBACK
        else:
            self.transport.write("DISPOSITIVO NO REGISTRADO".encode("utf-8"), addr)


protoDisp = Dispositivo()

reactor.listenUDP(9999, Servidor(protoDisp))
reactor.listenUDP(3060, protoDisp)
reactor.run()