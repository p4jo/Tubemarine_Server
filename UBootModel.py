# import atexit
import types
from abc import ABCMeta, abstractmethod
from typing import Optional, Tuple

class Motor(object):
    """Basisklasse für Motoren, macht an sich nichts."""

    def _set_internal(self, x: float, **kwargs):
        self.xVal = x
        # setze echten Motor o.ä. auf _mapping(x)

    def _mapping(self, x: float):
        """[xMin, xMax] --> [backwardsValue, forwardValue]: x = Steuerung value -> Motor value """
        if x > self.xMax:
            x = self.xMax
        if x < self.xMin:
            x = self.xMin

        if x > self.xZeroThreshold:
            return self.neutralPlus + self.xFactor * x
        if x < -self.xZeroThreshold:
            return self.neutralMinus + self.xFactor * x
        return self.neutralValue


    def value(self):
        return self._mapping(self.xVal)

    def _inverse_mapping(self, t: float):
        """ [backwardsValue, forwardValue] --> [xMin, xMax]: Motor value -> x = Steuerung value"""
        x = (t - self.neutralPlus) / self.xFactor
        if x <= 0: # t gehört eigentlich nicht ins positive Regime
            x = (t - self.neutralMinus) / self.xFactor
            if x >= 0: # t ist zwischen neutralMinus und neutralPlus
                x = 0

        # if x > self.xMax: # sollte eigentlich nicht passieren
        #     x = self.xMax
        # if x < self.xMin:
        #     x = self.xMin
        return x

    def __init__(self, backwardValue: float = -1.0, forwardValue: float = 1.0, neutralValue: Optional[float] = None, inc: Optional[float] = None, steuerung = None, minimalDeviation: Optional[float] = 0.0, xZeroThreshold: Optional[float] = None, **_):

        if backwardValue is None or backwardValue == '':
            backwardValue = -1.0
        if forwardValue is None or forwardValue == '':
            forwardValue = -1.0
        self.minimalDeviation = abs(minimalDeviation or 0.0)

        signum = (1 if forwardValue >= backwardValue else -1)

        if neutralValue is None or neutralValue == '':
            self.neutralValue = (forwardValue + backwardValue) / 2
        else:
            self.neutralValue = neutralValue

        self.neutralPlus = self.neutralValue + signum * self.minimalDeviation
        self.neutralMinus = self.neutralValue - signum * self.minimalDeviation

        if self.neutralPlus * signum > forwardValue * signum:  # signum = 1: neutralValue > forward >= backwards, signum = -1: neutralValue < forward <= backwards
            self.neutralValue = forwardValue
            self.neutralPlus = forwardValue
        elif self.neutralMinus * signum < backwardValue * signum:  # signum = 1: neutralValue < backwards <= forward, signum = -1: neutralValue > backwards > forward
            self.neutralValue = backwardValue
            self.neutralMinus = backwardValue

        if backwardValue == forwardValue:
            self.xMin = 0.0
            self.xMax = 0.0
            self.xFactor = 1.0
        else:
            fMn = forwardValue - self.neutralPlus # = Länge der positiven Range * signum
            nMb = self.neutralMinus - backwardValue # = Länge der negativen Range * signum
            ratio = fMn / nMb if nMb != 0.0 else 1e308  # sys.float_info.max ~ 1.7e308
            if ratio < 1.0:  # >= 0.0
                self.xMin = -1.0
                self.xFactor = nMb
                self.xMax = ratio  # = (f - n) / self.xFactor
            else:
                self.xMax = 1.0
                self.xFactor = fMn
                self.xMin = -1.0 / ratio  # = (b - n) / self.xFactor

        if inc is None:
            self.xInc = 0.05
        else:
            self.xInc = abs(inc / self.xFactor)
        if xZeroThreshold is None:
            self.xZeroThreshold = self.xInc * 0.6
        else:
            self.xZeroThreshold = abs(xZeroThreshold)

        self.xVal = 0.0
        # print(self.xMin,self.xMax,self.neutralValue)

        self.OnSet = []

        if steuerung is not None:
            self.steuerung = steuerung
        else:
            self.steuerung = types.SimpleNamespace(schreiben = print, fragen = input)


    def stop(self):
        self.set(0)

    def setToLowestValue(self):
        if self.xFactor >= 0:
            self.set(self.xMin)
        else:
            self.set(self.xMax)

    def setToHighestValue(self):
        if self.xFactor < 0:
            self.set(self.xMin)
        else:
            self.set(self.xMax)

    def increase(self, xInc: Optional[float] = None):
        if xInc is None:
            xInc = self.xInc
        self.set(self.xVal + xInc)

    def decrease(self, xInc: Optional[float] = None):
        if xInc is None:
            xInc = self.xInc
        self.set(self.xVal - xInc)

    def bootup(self):
        pass

    def set(self, x, dontThrowEvent = False, **kwargs):
        self._set_internal(x, **kwargs)
        if not dontThrowEvent:
            self._callOnChangedEvent()

    def _callOnChangedEvent(self):
        for ev in self.OnSet:
            ev(self.xVal)

    def __repr__(self):
        return f"Motor(x: {self.xMin:.3G}..0..{self.xMax:.3G}, output: {self._mapping(self.xMin):.3G}..{self._mapping(0):.3G}..{self._mapping(self.xMax):.3G})"


class SteeringMapping(metaclass = ABCMeta):
    """Abstract class for steering motors with speed and steering value. Encapsulates an injective function [-1,1]×[-1,1] --> [-1,1]×[-1,1], (steering, speed) -> (left, right) and its inverse (on its image)"""

    @abstractmethod
    def rightMapping(self, lenkung: float, speed: float) -> float:
        """Given the steering value lenkung and the speed value, computes the right motor value. This maps [-1,1]×[-1,1] --> [-1,1]"""
        pass

    @abstractmethod
    def leftMapping(self, lenkung: float, speed: float) -> float:
        pass

    @abstractmethod
    def steeringInverseMapping(self, leftMotorX: float, rightMotorX: float) -> float:
        pass

    @abstractmethod
    def speedInverseMapping(self, leftMotorX: float, rightMotorX: float) -> float:
        pass

    def LenkMotoren(self, leftMotor: Motor, rightMotor: Motor) -> Tuple[Motor, Motor]:
        """Entangles the two Motors with two new ones: A motor that represents the steering value (left: -1, forward: 0, right: 1) and a motor that represents the speed and return them in that order"""
        Lenkung = Motor()
        Speed = Motor()
        Lenkung.OnSet.append(lambda x: leftMotor.set(self.leftMapping(lenkung = x, speed = Speed.xVal), True))
        Lenkung.OnSet.append(lambda x: rightMotor.set(self.rightMapping(lenkung = x, speed = Speed.xVal), True))
        Speed.OnSet.append(lambda x: leftMotor.set(self.leftMapping(lenkung = Lenkung.xVal, speed = x), True))
        Speed.OnSet.append(lambda x: rightMotor.set(self.rightMapping(lenkung = Lenkung.xVal, speed = x), True))
        leftMotor.OnSet.append(lambda x: Lenkung.set(self.steeringInverseMapping(x, rightMotor.xVal), True))
        leftMotor.OnSet.append(lambda x: Speed.set(self.speedInverseMapping(x, rightMotor.xVal), True))
        rightMotor.OnSet.append(lambda x: Lenkung.set(self.steeringInverseMapping(leftMotor.xVal, x), True))
        rightMotor.OnSet.append(lambda x: Speed.set(self.speedInverseMapping(leftMotor.xVal, x), True))

        Lenkung.stop = lambda: None  # the steering motor doesn't have to change when stopping

        return Lenkung, Speed


class BasicSteeringMapping (SteeringMapping):

    def __init__(self, speedFactor: float = 1.05, steeringFactor: float = 1.75, **_):
        """speedFactor: Controls how much the speed is augmented (should be about 1).
        steeringFactor: Controls how much changing the steering value reduces the strength of the motor you steer towards. Should be in [1,2]."""
        self.speedFactor = speedFactor
        """Controls how much the speed is augmented (should be about 1)"""
        self.steeringFactor = steeringFactor
        """Controls how much changing the steering value reduces the strength of the motor you steer towards. Should be in [1,2]"""

    def _steeringFunction(self, steeringValue: float) -> float:
        """Given the steering value (towards the motor), computes the relative speed of the motor.
            The opposite motor will have the steering value -steeringValue. This maps [-1,1] --> [-1,1]."""
        if steeringValue < 0:
            return 1
        # Nullstelle bei 1/1.75 = 0.571
        return 1 - self.steeringFactor * steeringValue

    def _steeringInverseFunction(self, relativeSpeed: float) -> float:
        """Given the relative speed of the slower motor, gives the steering value. This maps [-steeringFactor/2,1] --> [-1,1] """
        return (1 - relativeSpeed)/self.steeringFactor

    def rightMapping(self, lenkung: float, speed: float) -> float:
        """Given the steering value lenkung and the speed value, computes the right motor value. This maps [-1,1]×[-1,1] --> [-1,1]"""
        return speed * self._steeringFunction(lenkung) * self.speedFactor

    def leftMapping(self, lenkung: float, speed: float) -> float:
        return speed * self._steeringFunction(-lenkung) * self.speedFactor

    def steeringInverseMapping(self, leftMotorX: float, rightMotorX: float) -> float:
        if abs(leftMotorX) < abs(rightMotorX):
            return -self.steeringInverseMapping(rightMotorX, leftMotorX)
        # speed == leftMotorX !
        if leftMotorX == 0:
            return 0
        return self._steeringInverseFunction(rightMotorX / leftMotorX)

    def speedInverseMapping(self, leftMotorX: float, rightMotorX: float) -> float:
        if abs(leftMotorX) < abs(rightMotorX):
            return self.speedInverseMapping(rightMotorX, leftMotorX)
        return leftMotorX

# jit_module()