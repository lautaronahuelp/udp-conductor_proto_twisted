from twisted.internet import reactor, task
from twisted.internet.protocol import DatagramProtocol 
import datetime

def cbLoopDone(result):
    """
    Called when loop was stopped with success.
    """
    print("Loop done.")
    reactor.stop()


def ebLoopFailed(failure):
    """
    Called when loop execution failed.
    """
    print(failure.getBriefTraceback())
    reactor.stop()

class Dispositivo(DatagramProtocol):
    def __init__(self):
        self._dispReg = {} #DISPOSITIVOS REGISTRADOS
        self._regPend = {} #DISPOSITIVOS REGISTRADO QUE CAMBIARON DE DIRECCION
        self._colaMensajes = [] #MENSAJES/COMANDOS PENDIENTES DE ENVIO

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
                                                        "ultimo_contacto": datetime.datetime.now(),
                                                        "secuencia": 1,
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

            if mensajeSplit[1] == "A":
                #AAAA|A|SSSS
                self.reconocimientoMensaje(mensajeSplit[0], mensajeSplit[2])
                    
                    
        
        print(self._dispReg)
    
    def enviarMensaje(self, mensaje, cuenta):
        #SSSS|M|MENSAJE
        if cuenta in self._dispReg:#esto se controla tambien en agregarMensaje
            self.transport.write(("%04d|M|%s" % ( self._dispReg[cuenta]["secuencia"], mensaje )).encode("utf-8"), self._dispReg[cuenta]["direccion"])
            return True
        else:
            return False

    def enviarSiguiente(self):
        if self._colaMensajes:
            if self._colaMensajes[0]["intento"]  < 4:
                self.enviarMensaje(self._colaMensajes[0]["mensaje"], self._colaMensajes[0]["cuenta"])
                self._colaMensajes[0]["intento"] += 1
            else:
                 self._colaMensajes.pop()#descarta mensaje que se intento enviar 4 veces
    
    def reconocimientoMensaje(self, cuenta, secuencia):
        if cuenta in self._dispReg:
            if self._dispReg[cuenta]["secuencia"] == int(secuencia):
                if self._colaMensajes:
                    self._colaMensajes.pop(0)#elimina el mensaje ya que secuencia coincide, corregir para multiples envios concurrentes
                    self._aumentaSecuencia(cuenta)

    def agregarMensaje(self, cuenta, mensaje):
        if cuenta in self._dispReg:
            self._colaMensajes.append({ 
                                        "cuenta": cuenta,
                                        "mensaje": mensaje,
                                        "intento": 0,
                                        })
            return True
        else:
            return False

    def _aumentaSecuencia(self, cuenta):
        self._dispReg[cuenta]["secuencia"] += 1

        if self._dispReg[cuenta]["secuencia"] > 9999:
            self._dispReg[cuenta]["secuencia"] = 1

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
        
        

        if self._protoDisp.agregarMensaje(mensajeSplit[0], mensajeSplit[2]):#LOS MENSAJES DEBEN ALMACENARSE EN UNA COLA Y SE EJECUTADOS POR EL REACTOR
            self.transport.write("AGREGADO A COLA".encode("utf-8"), addr)
        else:
            self.transport.write("DISPOSITIVO NO REGISTRADO".encode("utf-8"), addr)
    
    


protoDisp = Dispositivo()
protoServ = Servidor(protoDisp)

loop = task.LoopingCall(protoDisp.enviarSiguiente)

loopDeferred = loop.start(5.0)


# Add callbacks for stop and failure.
loopDeferred.addCallback(cbLoopDone)
loopDeferred.addErrback(ebLoopFailed)

reactor.listenUDP(9999, protoServ)
reactor.listenUDP(3060, protoDisp)
reactor.run()