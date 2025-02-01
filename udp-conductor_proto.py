from twisted.internet import reactor, task
from twisted.internet.protocol import DatagramProtocol 
import datetime

TIEMPO_INICIAL = datetime.datetime.strptime("10/17/1945 23:10:00", "%m/%d/%Y %H:%M:%S")
TIMEOUT_MENSAJE = 5 #TIMEOUT EN SEGUNDO PARA REPETIR EL ENVIO DE UN MENSAJE
TIEMPO_LOOP_ENVIA_MSJ = 0.2#CADA CUANTO SE REPITE EL LOOP DE enviaSiguiente

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
                    self._dispReg[item]["ultimoContacto"] = datetime.datetime.now()
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
                                                        "ultimoContacto": datetime.datetime.now(),
                                                        "secuencia": 1,
                                                        "mensajeAsignado": None,
                                                    }
                    
                    self.transport.write(("%s|R|OK" % mensajeSplit[0]).encode("utf-8"), addr)

            if mensajeSplit[1] == "T":#MENSAJE DE TEST
                
                if mensajeSplit[0] in self._dispReg:
                    dispositivo = self._dispReg[mensajeSplit[0]]
                    if dispositivo['direccion'] == addr:
                        dispositivo["ultimoContacto"] = datetime.datetime.now()
                        self.transport.write(("%s|A" % mensajeSplit[0]).encode("utf-8"), addr)

                    else:
                        self._regPend[mensajeSplit[0]] = self._dispReg.pop(mensajeSplit[0])

            if mensajeSplit[1] == "A":
                #AAAA|A|SSSS
                self.reconocimientoMensaje(mensajeSplit[0], mensajeSplit[2])
                    
                    
        
        print(self._dispReg)
    
    def enviarMensaje(self, mensaje):
        #SSSS|M|MENSAJE
        cuenta = mensaje["cuenta"]
        print("cola:" + str(self._colaMensajes))
        if cuenta in self._dispReg:#esto se controla tambien en agregarMensaje
            dispositivo = self._dispReg[cuenta]
            dispositivo["mensajeAsignado"] = mensaje["ingreso"]#asigna mensaje a la cuenta
            
            self.transport.write(("%04d|M|%s" % ( dispositivo["secuencia"], mensaje["mensaje"] )).encode("utf-8"), dispositivo["direccion"])
            mensaje["intento"] += 1
            mensaje["ultimoIntento"] = datetime.datetime.now()
            return True
        else:
            return False

    def enviarSiguiente(self):
        #buscar mensaje, comprobar si esta asignado al dispositivo o si se puede asignar(None), checkear intentos, chequear timeout
        if self._colaMensajes:

            
            for mensaje in self._colaMensajes:
                if mensaje["intento"]  < 4:
                    mensajeAsignado = self.getMensajeAsignado(mensaje["cuenta"])
                    if (mensajeAsignado == mensaje["ingreso"] or mensajeAsignado == None) and (datetime.datetime.now() - mensaje["ultimoIntento"]).total_seconds() > TIMEOUT_MENSAJE:
                        self.enviarMensaje(mensaje)
                else:
                    posEliminar = self._colaMensajes.index(mensaje)
                    self._colaMensajes.pop(posEliminar)#descarta mensaje que se intento enviar 4 veces
                    self.limMensajeAsignado(mensaje["cuenta"])
            

    def reconocimientoMensaje(self, cuenta, secuencia):
        #obtengo secuencia y mensaje asignado de la cuenta, desasigno mensaje, elimino mensaje de cuenta, y aumento secuencia
        if cuenta in self._dispReg:
            if self._dispReg[cuenta]["secuencia"] == int(secuencia):
                if self._colaMensajes:
                    self.eliminaMensajeCola(self._dispReg[cuenta]["mensajeAsignado"])
                    self._aumentaSecuencia(cuenta)
                    self._dispReg[cuenta]["mensajeAsignado"] = None

    def agregarMensaje(self, cuenta, mensaje):
        if cuenta in self._dispReg:
            self._colaMensajes.append({ 
                                        "cuenta": cuenta,
                                        "mensaje": mensaje,
                                        "ingreso": datetime.datetime.now(),
                                        "intento": 0,
                                        "ultimoIntento": TIEMPO_INICIAL,                      
                                    })
            return True
        else:
            return False

    def _aumentaSecuencia(self, cuenta):
        self._dispReg[cuenta]["secuencia"] += 1

        if self._dispReg[cuenta]["secuencia"] > 9999:
            self._dispReg[cuenta]["secuencia"] = 1
    
    def eliminaMensajeCola(self, ingreso):
        for mensaje in self._colaMensajes:
            if mensaje["ingreso"] == ingreso:
                self._colaMensajes.remove(mensaje)

    def getMensajeAsignado(self, cuenta):
        if self._dispReg:#esto ya lo controla agregarMensaje -> chequear si no se perdio comunicacion del dispositivo
            #falta corroborar que exista cuenta
            return self._dispReg[cuenta]["mensajeAsignado"]
        else:
            return None

    def limMensajeAsignado(self, cuenta):
        if self._dispReg:
            self._dispReg[cuenta]["mensajeAsignado"] = None

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

loopDeferred = loop.start(TIEMPO_LOOP_ENVIA_MSJ)


# Add callbacks for stop and failure.
loopDeferred.addCallback(cbLoopDone)
loopDeferred.addErrback(ebLoopFailed)

reactor.listenUDP(9999, protoServ)
reactor.listenUDP(3060, protoDisp)
reactor.run()