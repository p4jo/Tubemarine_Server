# import atexit
# import asyncio
import logging
from pathlib import Path
# import os
import time
from threading import Thread
from typing import Optional, Dict

# from numba import jit_module
from Motoren import loadMotorConfig
from UBootIO import curses, clearConsoleScreen, Schalter, Akkumesser, Lagesensor
from UBootModel import Motor

lineEnd = '\n\r'

import math
DEG_INV = 180 /  math.pi

class Steuerung(object):
    """Basisklasse für die Steuerung von Motoren und die Textausgabe"""
    loglevel: int = 6

    def schreiben(self, text, level = 1):
        if level <= self.loglevel:
            print(text)

    def fragen(self, question) -> bool:
        self.schreiben(question)
        return True

    def __init__(self, motoren: Dict[str, Motor] = None, initializeMotors=None):
        self.motoren = motoren
        self.onExit = []
        if self.motoren is None and initializeMotors is not None:
            try:
                self.motoren = loadMotorConfig(self, initializeMotors)
            except OSError as e:
                print("Motors could not be initialized:", e)
        if self.motoren is None:
            self.motoren = {"0": Motor()}
        # self.log(self.motoren)
        # atexit.register(self.stopAndQuit) # Tut nicht, da es auf Threads wartet. Die sollten aber damit beendet werden.

    def stop(self):
        for name in self.motoren:
            self.motoren[name].stop()

    def stopAndQuit(self): # Sollte WIRKLICH aufgerufen werden
        self.schreiben("Stoppe alle Motoren...")
        self.stop()
        self.quit()

    def quit(self):
        """Normally, you should call stopAndQuit instead (or stop yourself)"""
        self.schreiben("Räume extra Threads etc. auf")
        self.cleanupForExit()
        for f in self.onExit:
            f()

    def cleanupForExit(self):
        pass

    def onExitRegister(self, f):
        self.onExit.append(f)


class Konsolensteuerung(Steuerung):
    """Zum Testen per SSH"""

    def schreiben(self, text, level = 1):
        print(text, end = lineEnd)

    def fragen(self, question) -> bool:
        try:
            # return input(question) in ['j', 'y']
            self.schreiben(question)
            return self.screen.getch() in [ord('j'), ord('y')]
        except KeyboardInterrupt:
            return False

    def __init__(self, numbers: list = None, motoren=None, initializeMotors=None):

        super().__init__(motoren = motoren, initializeMotors = initializeMotors)
        self.screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.screen.keypad(True)
        if numbers is not None:
            self.numbers = numbers
        else:
            self.numbers = [*self.motoren]
        self.current = 0

        self.schalter = {}# {pin: Schalter(pin) for pin in pumpenSchalter}

        self.run()


    def run(self):

        # clearConsoleScreen()
        print("we have the following motors: ", *[f"{lineEnd}{key}: {self.motoren[key]}" for key in self.motoren],
              sep = "")  # , "with the following indices:", self.numbers)
        self.fragen("Los?")

        # program loop to control the RC car via a keyboard.
        self.current = self.numbers[0]
        try:
            while True:
                self.updateScreen()
                self.schreiben("Warte auf Eingabe...")
                timeSinceWaitingForChar = time.time()
                char = self.screen.getch()
                t: float = time.time()
                if 0 <= char < 0x110000:
                    self.schreiben(f"Eingabe: {chr(char)} nach {t-timeSinceWaitingForChar:.3f} Sekunden.")
                else:
                    self.schreiben("Seltsame Eingabe.")
                # print (char)
                # time.sleep(0.3)
                try:
                    self.current = self.numbers[int(char - 49)]
                    self.schreiben(f"Setze Motor auf {self.current}")
                    continue
                except IndexError:
                    pass

                try:
                    if char == ord('q'):
                        self.stop()

                    elif char == ord('b'):
                        # Hier muss man noch die Anzeige irgendwie freigeben

                        if self.fragen("Sollen wir den ESC starten?"):
                            self.motoren[self.current].bootup()
                    # end the program
                    elif char == ord('x'):
                        break

                    elif char == curses.KEY_UP:
                        print(f"Erhöhe Motor {self.current}... ", end = "")
                        self.motoren[self.current].increase()
                        tn = time.time()
                        self.schreiben(f"Dauerte {tn-t:.3f} Sekunden.")
                        t = tn
                    elif char == curses.KEY_DOWN:
                        # nonlocal t
                        print(f"Senke Motor {self.current}... ")
                        self.motoren[self.current].decrease()
                        tn = time.time()
                        self.schreiben(f"Dauerte {tn-t:.3f} Sekunden.")
                        t = tn
                except Exception as e:
                    self.schreiben(e)
                    time.sleep(1)
        except KeyboardInterrupt:
            pass
        self.schreiben("Abgebrochen durch Strg-C")
        self.stopAndQuit()
        exit(0)

    def updateScreen(self):
        clearConsoleScreen()
        
        self.schreiben("============ U-Boot-Steuerung ============")
        self.schreiben("\u2191/\u2193: Wert verändern")
        self.schreiben("\u2190/\u2192: left/right")
        self.schreiben("q:   Alle stoppen")
        self.schreiben("1,2,...: Auswählen des aktuellen Motors   ")
        self.schreiben("x:   Beenden")
        self.schreiben("b:   ESC hochfahren ")
        self.schreiben("================= Motoren ================")
        self.schreiben(f"Aktueller Motor: {self.current}")
        for name in self.motoren:
            self.schreiben(text = f"{name}: {self.motoren[name].xVal:.3G} ({self.motoren[name].value():.3G})")
        self.schreiben("================ Sensoren ================")
        for i in self.schalter:
            self.schreiben(text = f"Schalter {i} wurde {self.schalter[i].timesPressed} mal gedrückt.")
        self.schreiben(text= f"Beschleunigung (m/s²) {Lagesensor.linear_acceleration}")
        rot = "{:10.4f}, {:10.4f}, {:10.4f}".format(*[DEG_INV * r for r in Lagesensor.gyro])
        self.schreiben(text= f"Drehgeschwindigkeit (°/s) {rot}")
        self.schreiben(text= f"Lage als Euler-Winkel (°) {Lagesensor.euler}")
        self.schreiben(text= f"Gravitation (m/s²) {Lagesensor.gravity}")
        self.schreiben(text= f"Magnetfeld (µT) {Lagesensor.magnetic}")
        self.schreiben(text= f"Temperatur (°C) {Lagesensor.temperature}")
        self.schreiben(f"Akkustand: {Akkumesser.akkustand()}")

    def cleanupForExit(self):
        self.schreiben("Closing curses...")
        curses.nocbreak()
        self.screen.keypad(False)
        curses.echo()
        curses.endwin()

class InternetSteuerung(Steuerung):
    """Verarbeitet Befehle, die von der Tubemarine-App kommen."""

    lostConnectionTimeout: float = 10
    logFile = "/home/pi/InternetSteuerung.log"

    def schreiben(self, text: str, level: int = 1):
        logging.log(msg = text, level = level)
        if len(text) > 100:
            text = text[0:47] + '...' + text[-50:]
        if level <= self.loglevel:
            self.currentLog += text.strip() + '\n'

    def __init__(self, motoren=None, initializeMotors=None):
        super().__init__(motoren = motoren, initializeMotors = initializeMotors)
        self.running = True
        self.oldData = dict()
        self.lastSentTime = dict()

        self.currentLog = ""

        self.lastConnectionTime = time.time() + 10
        self.waitingForLostConnectionThread: Optional[Thread] = Thread(target = self.run_async)
        self.waitingForLostConnectionThread.start()
        # self.waitingForLostConnectionThread = asyncio.ensure_future(self.run_async())
        # asyncio.get_event_loop().run_until_complete(self.waitingForLostConnectionThread)

        if not Path(InternetSteuerung.logFile).parent.exists():
            InternetSteuerung.logFile = Path(__file__).parent / 'InternetSteuerung.log'
        logging.basicConfig(filename = InternetSteuerung.logFile, level = self.loglevel)

    def handleMessage(self, message: str):
        message = message.lower().strip()
        if message == "stop":
            self.stop()

    def onReceive(self, newData: dict):
        self.lastConnectionTime = time.time()

        # messages
        sentTime = newData.pop("sentTime", time.time())
        message = newData.pop("message", '')
        self.schreiben("received: " + str(newData), 10)

        self.handleMessage(message)

        # motorValues
        for key in newData:
            value = newData[key]
            self.schreiben(str(key) + ": " + str(value) + " of headerType " + str(type(value)), 15)
            if key in self.lastSentTime and sentTime < self.lastSentTime[key]:
                self.schreiben(
                    f"Overlap on inputs for {key}: this is {self.lastSentTime[key] - sentTime:.3G}s older than the last value",
                    2)
            else:
                self.lastSentTime[key] = sentTime

            if key not in self.oldData or abs(self.oldData[key] - value) > 0.01:
                if key in self.motoren:
                    try:
                        if False and hasattr(self.motoren[key], "setSlow"):
                            self.motoren[key].setSlow(float(value))
                        else:
                            self.motoren[key].set(float(value))
                    except Exception as e:  # wirft eigentlich keine
                        self.schreiben(f"Motor {key} konnte nicht auf {value} gesetzt werden, denn {e}", 1)
                else:
                    self.handleMessage(f"{key}: {value}")

        self.oldData['akkuHealth'] = Akkumesser.akkustand()
        self.oldData['sensorData'] = dict()
        for d in ['linear_acceleration', 'gravity', 'gyro', 'euler', 'magnetic', 'temperature']:
            r = getattr(Lagesensor, d, 'null') 
            if isinstance(r, tuple):
                r = list(r) # jsonpickle encodes tuples weirdly [maybe use jsonpickle options like unpickleable or preferred_backend=json]
            self.oldData['sensorData'][d] = r
        self.oldData['log'] = self.currentLog
        self.currentLog = ''
        for key in self.motoren:
            self.oldData[key] = self.motoren[key].xVal

        return self.oldData

    def run_async(self):
        try:
            while self.running:
                waitTime =  self.lastConnectionTime + self.lostConnectionTimeout - time.time()
                if waitTime > 1E-5:
                    time.sleep(waitTime)
                    # await asyncio.sleep(waitTime)
                else:
                    self.OnLostConnection()
                    self.lastConnectionTime = time.time()
                    # time.sleep(self.lostConnectionTimeout)
                    # await asyncio.sleep(waitTime)
        except:
            self.stop()
            # await self.run_async()
            self.run_async()

    def OnLostConnection(self):
        self.stop()
        self.schreiben('STOPPED BECAUSE OF DISCONNECT')


    def cleanupForExit(self):
        self.running = False
        self.waitingForLostConnectionThread.join(0.5)
        # self.waitingForLostConnectionThread.cancel()



# pumpenSchalter = {
#     16: -1.0,
#     20: 0.0,
#     21: 1.0
# }
# def motorConfiguration(steuerung: Steuerung) -> Dict[str, Motor]:
#     # linker Motor # Kann eigentlich auch -1 bis 1 (alle optionalen Argumente weglassen)
#     linkerMotor = ESCMotor(8, -0.125, 0.125, steuerung = steuerung, minimalDeviation = 0.06)
#     rechterMotor = ESCMotor(0, -0.125, 0.125, steuerung = steuerung, minimalDeviation = 0.06)
#     lenkungFakeMotor, speedFakeMotor = BasicSteeringMapping().LenkMotoren(linkerMotor, rechterMotor)
#
#     # pumpenMotor = ESCMotor(10, -0.53, 0.53, minimalDeviation = 0.2, steuerung = steuerung) # Hört bei Werten im Betrag > 0.95 einfach auf. Werte im Betrag > 0.5 machen ihn nicht mehr schneller (zumindest in Luft)
#     pumpenMotor = ESCMotor(10, -0.6, 0.4, neutralValue = -0.1, minimalDeviation = 0.2, steuerung = steuerung)
#     # pumpenMotor = ESCMotor(10, -0.7, 0.3, neutralValue = -0.2, minimalDeviation = 0.2, steuerung = steuerung)
#
#     # pumpenMotor = ESCMotor(10, -0.05, -1,steuerung = steuerung, neutralValue = -0.7, minimalDeviation = 0.2 ) # War einmal so. Irgendwie nicht sicher. Hat da aber bei 0 (und -0.7) auch aufgehört
#     lampenMotor = ESCMotor(11, steuerung = steuerung)
#
#     return {
#         "Kamera":               ServoMotor(12, 180, 0, steuerung = steuerung),
#         "Auftriebsmotor":       pumpenMotor,
#         "Links":                linkerMotor,
#         "Rechts":               rechterMotor,
#         "Lampenmotor":          lampenMotor,
#         "Lampe":                ServoESCMotor(motor = lampenMotor, steuerung = steuerung),
#         "Auftrieb":             ServoESCMotor(motor = pumpenMotor, sensorConfig = pumpenSchalter, vMax =1 / 14, steuerung = steuerung),
#         "Lenkung":              lenkungFakeMotor,
#         "Speed":                speedFakeMotor
#     }


if __name__ == "__main__":
    from MotorSetupController import MotorSetupController
    MotorSetupController(cls=Konsolensteuerung)

# jit_module()
