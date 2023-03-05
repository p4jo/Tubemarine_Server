import asyncio
import json
import os
import time
from threading import Thread
from typing import Optional, Dict

from UBootIO import PhysicalMotors, Schalter, DummyMotorInterface, Potentiometer
from UBootModel import Motor, BasicSteeringMapping
from timetest import timeTest

class ESCMotor(Motor):
    slowSetSleepTime_s = 0.2

    def bootup(self):
        # global self.steuerung
        # if (self.steuerung is not None):
        self.steuerung.schreiben("Setze auf -1")
        self.setToLowestValue()
        self.steuerung.fragen("Anschalten! 3 mal gepiept und jetzt Dauer-piepend? Dann weiter.")
        time.sleep(0.5)
        self.steuerung.schreiben("Setze auf 0")
        self.set(0)
        self.steuerung.fragen("Sollte 'lang' piepen. Dann fertig.")

    def __init__(self, servoID: int, backwardValue: float = -1.0, forwardValue: float = 1.0,
                 neutralValue: Optional[float] = None, inc: Optional[float] = None, minimalDeviation: float = 0,
                 steuerung=None, xZeroThreshold: Optional[float] = None, **_):
        """
        @type steuerung: Steuerung
        """
        super().__init__(backwardValue, forwardValue, inc = inc, neutralValue = neutralValue, steuerung = steuerung, minimalDeviation = minimalDeviation, xZeroThreshold = xZeroThreshold)
        self.slowTarget = 0.0 # not active yet
        try:
            # Sollte Fehler schmeißen, wenn servoID nicht 0 bis 15 ist.
            self.motor = PhysicalMotors.continuous_servo[servoID]
        except ZeroDivisionError:
            print("ES GAB EINEN INTERNEN FEHLER BEIM SETZEN VON WERTEN FÜR DEN ADAFRUIT CONTROLLER")
            self.motor = DummyMotorInterface()

        self.changeSpeed = 0.5 # xVal/s

        def run_async():
            lastSetTime = time.time()
            while True:
                remainingChange = self.slowTarget - self.xVal
                currentTime = time.time()
                elapsedTime = currentTime - lastSetTime
                # if abs(elapsedTime - self.slowSetSleepTime_s) > 0.1 * self.slowSetSleepTime_s:
                #     print(f"time.sleep slept the wrong time: {elapsedTime} instead of {self.slowSetSleepTime_s}")

                lastSetTime = currentTime
                if remainingChange > 0:
                    self._set_internal(self.xVal + min(self.changeSpeed * elapsedTime, remainingChange))
                else:
                    self._set_internal(self.xVal + max(-self.changeSpeed * elapsedTime, remainingChange))

                time.sleep(self.slowSetSleepTime_s)

        def stopSlowOnSet(newXVal):
            self.slowTarget = newXVal

        self.OnSet.append(stopSlowOnSet)

        # self.thread = Thread(target=run_async)
        # self.thread.start()

    def __repr__(self):
        return f"ESCMotor(physicalMotor={self.motor},{os.linesep}\tx: {self.xMin:.3G}..(±{self.xZeroThreshold:.3G})..{self.xMax:.3G}, output: {self._mapping(self.xMin):.3G}..({self._mapping(0):.3G}±{self.minimalDeviation:.3G})..{self._mapping(self.xMax):.3G})"

    # @timeTest(log = lambda self, text: self.steuerung.schreiben(text, 11), alertRepeat = 5000, alertTime = 0.25)
    def _set_internal(self, x, **kwargs):

        # print(self.xVal, self.motor.angle, "->", x, self.mapping(x))
        #   #input("ok")
        # time.sleep(0.5)
        # if abs(x) < self.xZeroThreshold:
        # x = sign(x) * self.xZeroThreshold # Braucht man noch einen

        if abs(x) < self.xZeroThreshold:
            x = 0.0

        newVal = self._mapping(x)

        if abs(x - self.xVal) > 1e-5:
            # braucht recht lange
            if newVal is None or x == 0.0:
                self.motor.fraction = None
                print("set to None when stopping")
                self.xVal = 0.0
            else:
                self.motor.throttle = newVal
                self.xVal = self._inverse_mapping(self.motor.throttle)
                # Da das selbst eine Logik hat und nur einen nahe liegenden Wert nimmt.

            # if abs(self.xVal) < self.xZeroThreshold:
            #     self.xVal = 0.0

    def setSlow(self, x, **kwargs):
        self.slowTarget = x

    def value(self):
        try:
            a = self.motor.fraction
            if a is None:
                return 0.0
            return a*2-1
            # return self.motor.throttle
        except:
            print("WTF, ich konnte den Wert vom Motor nicht auslesen")
            return 0.0

    def correctZero(self, tooHighValue):
        changeValue = - tooHighValue * self.xFactor
        self.neutralValue += changeValue
        self.steuerung.schreiben(f"Corrected Zero Value of {self} by {changeValue}. It is now {self.neutralValue}")
        if self.neutralPlus < self.neutralValue:
            self.steuerung.schreiben(f"Corrected Value is outside of the zero threshold regime (neutralMinus < neutralValue < neutralPlus): {self.neutralMinus} < {self.neutralValue} !< {self.neutralPlus}. Will set it to {self.neutralPlus}")
            self.neutralValue = self.neutralPlus
        else:
            self.steuerung.schreiben(f"Corrected Value is outside of the zero threshold regime (neutralMinus < neutralValue < neutralPlus): {self.neutralMinus} !< {self.neutralValue} < {self.neutralPlus}. Will set it to {self.neutralMinus}")
            self.neutralValue = self.neutralMinus



class ServoMotor(Motor):

    def __init__(self, servoID: int, minValue: float, maxValue: float, neutralValue: Optional[float] = None, inc: Optional[float] = None, steuerung = None, **_):
        super().__init__(minValue, maxValue, inc = inc, neutralValue = neutralValue, steuerung = steuerung)
        try:
            self.motor = PhysicalMotors.servo[servoID]  # Sollte Fehler schmeißen, wenn servoID nicht 0 bis 15 ist.
        except ZeroDivisionError:
            print("ES GAB EINEN INTERNEN FEHLER BEIM SETZEN VON WERTEN FÜR DEN ADAFRUIT CONTROLLER")
            self.motor = DummyMotorInterface()

    def __repr__(self):
        return f"ServoMotor(physicalMotor={self.motor},{os.linesep}\tx: {self.xMin:.3G}..0..{self.xMax:.3G}, output: {self._mapping(self.xMin):.3G}..{self._mapping(0):.3G}..{self._mapping(self.xMax):.3G})"

    @timeTest
    def _set_internal(self, x):
        # os.system('clear')
        # print(self.xVal, self.motor.angle, "->", x, self.mapping(x))
        # input("ok")
        # time.sleep(0.5)

        self.motor.angle = self._mapping(x)
        # Da das selbst eine Logik hat und nur einen nahe liegenden Wert nimmt.
        self.xVal = self._inverse_mapping(self.motor.angle)

    def stop(self):
        pass
        # self.motor.angle = self.motor.angle


class ServoESCMotor(ServoMotor):
    """Soll wie ServoMotor verwendet werden können, ist aber ein ESCMotor. Muss Position aus der Zeit erraten, die es sich dreht. Braucht Endschalter  # Braucht vielleicht einen neutrale Stellung-Schalter (für die Pumpen)"""
    minUpdateTime = 0.002
    maxUpdateTime = 1.0 / 60
    # xGoal: float
    # vMax: float # Maximum velocity dx/dt / (1/s)
    # motor: ESCMotor
    def __init__(self, motor: ESCMotor, sensorConfig: dict = None, minValue: float = -1.0,
                 maxValue: float = 1.0, inc=None, neutralValue: Optional[float] = None,
                 vMax=0.1, DontTrustZeroOfMotor = False, steuerung = None, **_
                 ):
        """
            servoID is the id of the actual motor on Adafruit, 
            limitSwitchesConfig is a dict: pin -> xVal where pin is the GPIO pin of a switch and xVal is the value that this ServoESCMotor is on when the switch is activated.
            An entry pin -> "{min},{max}" stands for a Potentiometer (Voltmeter pin {pin}) with xVal <-> potentiometer.value of -1 <-> {min}, 1 <-> {max}
        """
        Motor.__init__(self, minValue, maxValue, inc = inc, neutralValue = neutralValue, steuerung = steuerung)
        self.xValLastCorrected = time.time() - 100000
        self.running = False
        self.passive = False
        self.vMax = vMax
        self.DontTrustZeroOfMotor = DontTrustZeroOfMotor
        self.motor = motor
        self.thread= None

        self.limitSwitches = []
        self.lastValueUpdate = time.time()
        self.equalThreshold = self.xInc / 3.0
        self.transitionWidth = self.xInc * 2
        self.xGoal = 0

        if isinstance(sensorConfig, str):
            sensorConfig = json.loads(sensorConfig)

        if sensorConfig is not None:
            for key in sensorConfig:
                try:
                    pin = int(key)
                except:
                    print("The keys of sensorConfig must be integers. sensor Config was", sensorConfig)
                else:
                    try:
                        xVal = float(sensorConfig[key])
                        self.limitSwitches.append(Schalter(pin=pin, callback=lambda: self.reachedValue(xVal)))
                    except:
                        try:
                            min, max = sensorConfig[key].split(",")
                            min = float(min)
                            max =  float(max)
                            diff = max - min
                            slope = 2/diff
                            def callback(value):
                                self.reachedValue(-1 + slope * (value - min))
                            self.limitSwitches.append(Potentiometer(pin=pin, callback=callback))
                        except Exception as e:
                            print("Couldn't understand sensor Config", sensorConfig[key], "Error: ", e)


        self.activate()
        self.makePassive()
        self.motor.OnSet.append(lambda *args: self.makePassive())

        self.steuerung.onExitRegister(lambda: self.deactivate())
        # atexit.register(lambda: self.deactivate())

    def reachedValue(self, xVal):
        self.steuerung.schreiben(f"Sensor sagt mir, ich bin bei {xVal} angekommen. Ich bin ein ServoESC.", 11)
        if (self.motor.xVal > 0 and xVal >= 1) or (self.motor.xVal < 0 and xVal <= -1):
            self.motor.stop()
            print('STOPPED AT BORDER')
        # stopped but moved nonetheless. Could be because the ESC has a wrong zero!
        if self.DontTrustZeroOfMotor and self.isStopped() and abs(self.xVal - xVal) > 1e-5:
            self.motor.correctZero((xVal - self.xVal)/((time.time() - self.lastValueUpdate) * self.vMax ))
            # that is the amount we would expect motor.xVal to be when it drifted xVal-self.xVal in time.time() - self.lastValueUpdate seconds
        # correct with self.xGoal-xVal
        self.updateMotor(xVal)
        self.xValLastCorrected = time.time()

    def _set_internal(self, x: float = 0):
        self.xGoal = x
        self.activate()
        self.updateMotor()

    def updateMotor(self, newVal: Optional[float] = None):
        newTime = time.time()
        if newVal is None:
            if len(self.limitSwitches) > 0 and hasattr(self.limitSwitches[-1], "location"):
                newVal = self.limitSwitches[-1].location()
            else:
                newVal = self.xVal + (newTime - self.lastValueUpdate) * self.vMax * self.motor.xVal  # Approximation
        if newVal > 1:
            newVal = 1
        if newVal < -1:
            newVal = -1
        self.xVal = newVal
        self.lastValueUpdate = newTime
        if not self.passive:
            # Es normal zu setzen würde diesen Steuerungsmotor passiv machen
            self.motor.setSlow(self.transition(self.xGoal - newVal), dontThrowEvent=True)

    def transition(self, x):
        if x < 0:
            return -self.transition(-x)
        if x < self.equalThreshold:
            return 0.0
        return (x - self.equalThreshold) / (self.transitionWidth - self.equalThreshold)

    def stop(self):
        self.motor.stop() # deaktiviert auch diesen Motor
        self.xGoal = self.xVal

    def bootup(self):
        self.motor.bootup()

    def activate(self):
        self.running = True
        self.passive = False

        if self.thread is None:
            self.thread = Thread(target = self.async_run)
            self.thread.start()
        # self.thread = asyncio.ensure_future(self.async_run())
        # asyncio.get_event_loop().run_until_complete(self.thread)

    def deactivate(self):
        self.running = False
        self.thread = None

    def async_run(self):  # Sollte in extra Thread oder so laufen
        self.lastValueUpdate = time.time()
        while self.running:
            self.updateMotor()
            sleepTime = abs(self.xGoal - self.xVal) / self.vMax / 2
            if sleepTime < self.minUpdateTime:
                sleepTime = self.minUpdateTime
            if sleepTime > self.maxUpdateTime:
                sleepTime = self.maxUpdateTime
            time.sleep(sleepTime)
            # await asyncio.sleep(sleepTime)

    def value(self):
        # return self.xGoal
        return self.xVal

    def makePassive(self):
        self.passive = True

    def isStopped(self):
        return self.xVal == self.xGoal and time.time() - self.xValLastCorrected < 60

# jit_module
def loadMotorConfig(steuerung, config: Dict[str, Dict[str, str]]):
    res = {}
    servoESCs = []
    steeringSpeedMotors = []

    if not isinstance(config, dict):
        raise Exception(f"Wrong type for motorConfig")

    for name in config:
        c = config[name]
        t = c['type'].lower().strip()
        motor: Motor
        if t.startswith("servoesc"):
            servoESCs.append(name)
        elif t.startswith("steering") or t.startswith("speed"):
            steeringSpeedMotors.append(name)

        elif t.startswith('esc'):
            res[name] = ESCMotor(steuerung=steuerung, **c)
        elif t.startswith("servo"):
            res[name] = ServoMotor(steuerung=steuerung, **c)
        else:
            raise Exception(f"Wrong type in Motor definition json: {c['type']}. Supported: ESC, Servo, ServoESC (acts like a servo but is an ESC with position measurement), Steering, Speed (fake motors controlling ESCs)")

    for name in servoESCs:
        c = config[name]
        # noinspection PyTypeChecker
        c['motor'] = res[c['motor']]
        res[name] = ServoESCMotor(steuerung=steuerung, **c)

    # sort speed/steering motors with the same left/right together
    leftRightToSpeedSteering = {}
    for name in steeringSpeedMotors:
        c = config[name]
        t = c['type'].lower().strip()
        index = (c['left'], c['right'])
        if index not in leftRightToSpeedSteering:
            leftRightToSpeedSteering[index] = [('', {}), ('', {})]
        if t.startswith('steering'):
            leftRightToSpeedSteering[index][0] = (name, c)
        elif t.startswith('speed'):
            leftRightToSpeedSteering[index][1] = (name, c)

    for index in leftRightToSpeedSteering:
        leftMotorName, rightMotorName = index
        # (speedMotorName, speedMotorConfig) , (steeringMotorName, steeringMotorConfig)= leftRightToSpeedSteering[index]
        steeringMotorNameAndConfig, speedMotorNameAndConfig = leftRightToSpeedSteering[index]
        speedMotorName, speedMotorConfig = speedMotorNameAndConfig
        steeringMotorName, steeringMotorConfig = steeringMotorNameAndConfig

        # create the fake motors
        steeringFakeMotor, speedFakeMotor = BasicSteeringMapping(
                **(speedMotorConfig or steeringMotorConfig)
        ).LenkMotoren(
            res[leftMotorName],
            res[rightMotorName]
        )
        if len(speedMotorConfig) > 0:
            res[speedMotorName] = speedFakeMotor
        if len(steeringMotorConfig) > 0:
            res[steeringMotorName] = steeringFakeMotor

    return res
