# import asyncio
import atexit
import os
import platform
import time
import numpy as np
from abc import abstractmethod
from threading import Thread

# import busio
# import board # Adafruit.Blinka  board, not the standard pip board !!

#region I2C Addresses and Parameters

Ina3221ThreeCellLipoAkkumesserAddress = 0x42
AdafruitServoControllerAddress = 0x41
LagesensorAddress = 0x29
VoltmeterAddress = 0x48
VoltmeterGain = 1.0 # default 1
VoltmeterPotentiometerPin = 0 # 0..3
VoltmeterWatchInterval_s = 0.3
VoltmeterSampleRate_Hz = 64 # 8..860, default 128
VoltmeterWatchThreshold_cm = 0.15

#endregion
try:
    import board
    i2c = board.I2C()
except NotImplementedError as e:
    i2c = None
    print("NO I2C DETECTED ON THIS BOARD:", e)
    print("NOTHING WILL WORK!!")

#region PhysicalMotors
class DummyMotorInterface:
    def __init__(self):
        self.throttle = 0.0
        self.angle = 0.0

    def __repr__(self):
        return "DummyMotorInterface(\"USELESS!\")"


class DummyPhysicalMotors:
    frequency = 50
    continuous_servo = [DummyMotorInterface() for _ in range(16)]
    servo = [DummyMotorInterface() for _ in range(16)]


try:
    from adafruit_servokit import ServoKit

    PhysicalMotors = ServoKit(channels = 16, address = AdafruitServoControllerAddress, frequency = 60, i2c = i2c)
except ModuleNotFoundError:
    print("MOTORS WILL NOT WORK, because the Adafruit ServoKit is not installed. ")
    PhysicalMotors = DummyPhysicalMotors()
# except ValueError as exception:
except Exception as exception:
    print("####################################\nTHE ADAFRUIT SERVO CONTROLLER IS NOT PROPERLY CONNECTED: ",
          exception,
          "MOTORS WILL NOT WORK\n###################################")
    PhysicalMotors = DummyPhysicalMotors()


#endregion

#region Akkumesser

class Ina3221ThreeCellLipoAkkumesser:

    minAll_V = 11.4
    maxAll_V = 12.4
    diffAll_V = maxAll_V - minAll_V
    minSingle_V = 3.5
    maxSingle_V = 4.1
    diffSingle_V = maxSingle_V - minSingle_V

    penaltyLowSingle = 0.15
    tooLowThresholdSingle = 0.15

    def rawVoltages(self):
        try:
            return [self.device.getBusVoltage_V(channel = channel) for channel in [1,2,3]]
        except Exception as exception:
            print(f"Fehler beim Auslesen der Spannungen am Akku: {exception}")
            return [0.0, 0.0, 0.0]

    def cellVoltages(self):
        voltages_V = self.rawVoltages()
        voltages_V.sort()
        return [voltages_V[0], voltages_V[1] - voltages_V[0], voltages_V[2]-voltages_V[1]]

    def akkustand(self) -> float:
        cells = self.cellVoltages()

        totalHealth = min((sum(cells) - self.minAll_V) / self.diffAll_V, 1)

        cellHealth = [min((v - self.minSingle_V) / self.diffSingle_V, 1) for v in cells]

        return totalHealth - self.penaltyLowSingle * sum([self.tooLowThresholdSingle - s for s in cellHealth if s < self.tooLowThresholdSingle])

    def __init__(self, device):
        self.device = device

try:
    import Spannungsmesser.SDL_Pi_INA3221 as Strommesser

    Akkumesser = Ina3221ThreeCellLipoAkkumesser(device = Strommesser.SDL_Pi_INA3221(addr = Ina3221ThreeCellLipoAkkumesserAddress))

except Exception as e:
    print("Der Ina3221 Drei-Zellen-LiPo-Akkumesser konnte nicht initialisiert werden. Der Akkustand wird immer als 69% gemeldet! Message:", e)

    class DummyAkkumesser:
        minAll_V = 11.4
        maxAll_V = 12.4
        diffAll_V = maxAll_V - minAll_V
        minSingle_V = 3.5
        maxSingle_V = 4.1
        diffSingle_V = maxSingle_V - minSingle_V

        penaltyLowSingle = 0.15
        tooLowThresholdSingle = 0.15
        def cellVoltages(self):
            return []
        def rawVoltages(self):
            return []

        def akkustand(self):
            return 0.69

    Akkumesser = DummyAkkumesser()

#endregion

#region Überwachen
class Wertüberwacher:
    @abstractmethod
    def internalCallback(self):
        pass
    @abstractmethod
    def setup(self, callback):
        pass

    _callbackList = {} # dict[list[callable]]

    @staticmethod
    def _callCallbacks(name, *args):  # Only one callback given to GPIO add_event_detect
        if name in Wertüberwacher._callbackList:
            for callback in Wertüberwacher._callbackList[name]:
                try:
                    callback(*args)
                except TypeError:
                    callback()

    def getCallbackForEventSource(self):
        """This callback should be used and only be used in setup(self) which itself should not be called directly. """
        return lambda *args: Wertüberwacher._callCallbacks(self.name, *args)

    def __init__(self, name, callback=None):
        self.name = name
        
        if name not in Schalter._callbackList:
            self.setup(self.getCallbackForEventSource())
            Schalter._callbackList[name] = []

        Wertüberwacher._callbackList[name].append(lambda: self.internalCallback()) # self.internalCallback != () => self.internalCallback()
        if callback:
            Wertüberwacher._callbackList[name].append(callback)

#endregion

#region Schalter
try:
    from RPi import GPIO
    # GPIO.setmode(GPIO.BOARD) # Use physical pin numbering # ValueError: A different mode has already been set!
except ModuleNotFoundError:
    print("NOT RUNNING ON RASPBERRY PI. INPUT/OUTPUT WILL NOT WORK AT ALL!")
    class DummyGPIO:
        IN = 0
        PUD_DOWN = 2
        RISING = 10

        def setup(self, pin, mode, pull_up_down):
            print("Dieser Versuch, einen GPIO Pin als Schalter zu verwenden, wird nichts bringen, da GPIO NICHT ANGESCHLOSSEN ist!")

        def add_event_detect(self, pin, event, callback):
            pass

        def cleanup(self):
            pass
    GPIO = DummyGPIO()


class Schalter(Wertüberwacher):
    def __init__(self, pin: int, callback=None):
        self.timesPressed = 0
        self.pin = pin
        super().__init__(name=f"Schalter {pin}", callback=callback)
        
    def setup(self, callback):
        pin = self.pin
        try:
            # GPIO.setup(pin, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
            GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.add_event_detect(pin, GPIO.FALLING, callback=callback)
        except Exception as e:
            print(f"GPIO PIN {pin} COULD NOT BE SET UP: {e}")
            self.timesPressed = -1

    def internalCallback(self):
        self.timesPressed += 1
        print(f"{self.name} zum {self.timesPressed}. mal gedrückt.")

def SchalterTest():
    print("Gebe Schalter-Nummer (pin) zum Testen ein: ")
    try:
        schalterID = int(input())
    except:
        print("Muss eine natürliche Zahl sein (inkl. 0)")
        return
    Schalter(pin=schalterID)

#endregion

#region Lagesensor
try:
    from adafruit_bno055 import BNO055_I2C
    Lagesensor = BNO055_I2C(i2c=i2c, address=LagesensorAddress)
except Exception as exception:
    print("Der BNO055 Lagesensor (und mehr) konnte nicht initialisiert werden. Message: ", exception)
    class DummyLagesensor:
        def __init__(self):
            self.linear_acceleration = [0.0, 0.0, 0.0]
            self.gravity = [0.0, 0.0, -9.81]
            self.gyro = [0.0, 0.0, 0.0]
            self.euler = [0.0, 0.0, 0.0]
            self.magnetic = [0.0, 0.0, 0.0]
            self.temperature = 0
    Lagesensor = DummyLagesensor()

def Lagesensor_Test():
    print(f"""
Beschleunigung: {Lagesensor.linear_acceleration} m/s²
Gravitation: {Lagesensor.gravity} m/s²
Gyro: {Lagesensor.gyro} rad/s
Ausrichtung: {Lagesensor.euler}
Magnetfeld: {Lagesensor.magnetic} μT
Temperatur: {Lagesensor.temperature} °C
""")
#endregion

#region Potentiometer-Spannungssensor
# https://learn.adafruit.com/adafruit-4-channel-adc-breakouts/
try:
    from adafruit_ads1x15.ads1115 import ADS1115
    from adafruit_ads1x15.analog_in import AnalogIn

    ADS_Instance = ADS1115(i2c=i2c, gain=VoltmeterGain, address=VoltmeterAddress, data_rate=VoltmeterSampleRate_Hz)
except Exception as exception:
    print("####################################\nTHE ADAFRUIT VOLTMETER IS NOT PROPERLY CONNECTED: ",
          exception,
          "THE POSITIONING OF THE LIFTING BODY WILL NOT WORK. DON'T USE IT \n###################################")
    class DummyADS1x15:
        def read(self, *args):
            return 0
        def __init__(self):
            self.gain = 1
            self.bits = 16
    ADS_Instance = DummyADS1x15() 
    
    class AnalogIn: # Dummy
        def __init__(self, *_):
            self.voltage=0   

class Potentiometer(Wertüberwacher):
    def __init__(self, pin, callback=None, averageTime=0.3):
        self.pin = pin
        self.Voltmeter = AnalogIn(ADS_Instance, pin)
        super().__init__(name=f"Potentiometer {pin}", callback=callback)
        self.thread = None
        self.averageTime = averageTime

        self.errors=0
        self.worked=0
        self.lastValues= np.array([],dtype='float')
        self.lastTimes = np.array([],dtype='float')

    def setup(self, callback):
        def async_run():
            lastReportedValue = -100000000.0
            while True:
                # await asyncio.sleep(VoltmeterWatchInterval_s)
                time.sleep(VoltmeterWatchInterval_s)
                # print('\'', end="", flush=True)
                newValue = self.location()
                if abs(lastReportedValue - newValue) > VoltmeterWatchThreshold_cm:
                    print(f"changed value on voltmeter with pin {self.pin} from {lastReportedValue} to {newValue}")
                    lastReportedValue = newValue
                    callback(newValue)
            
        self.thread = Thread(target=lambda: async_run())
        self.thread.start()
        # try:
        #     self.thread = asyncio.create_task(async_run())
        # except:
        # self.thread = asyncio.ensure_future(async_run())
        # asyncio.set_event_loop_policy()
        # asyncio.get_event_loop().run_until_complete(self.thread)

    def internalCallback(self):
        print(f"{self.name} auf {self.location()} cm verschoben.")

    def location(self):
        """ Die Position des Schiebers in cm, zwischen 0.09 und 9.75 (eigentlich 0 und 9.7). """
        try:
            U = self.Voltmeter.voltage
        except OSError as e:
            if e.errno == 121:
                self.errors += 1
            else: raise
        else:
            self.worked += 1

            val = -1.8686 * U**3 + 0.0998 * U**2 - 5.1519 * U + 9.7939 # Interpolation als Polynom 3. Grades der 10 Messwerte

            t = time.time()
            i = 0
            while i < len(self.lastTimes) and self.lastTimes[i]  < t - self.averageTime:
                i += 1
            self.lastTimes = np.append(self.lastTimes, t)[i:]
            self.lastValues =  np.append(self.lastValues, val)[i:]

        if (self.worked + self.errors) % 10 == 0 and self.worked < 8 * self.errors:
            print(f"{self.worked} worked, {self.errors} errors when reading voltmeter value")
            
        return np.average(self.lastValues).item()

    def voltage(self):
        return self.Voltmeter.voltage


def PotentiometerTest():
    print("Gebe Potentiometer-Nummer (pin) zum Testen ein: ")
    try:
        potentiometerID = int(input())
    except:
        print("Muss eine natürliche Zahl sein (inkl. 0)")
        return
    p = Potentiometer(pin=potentiometerID)
    print(f"current Value: {p.location()}")

#endregion


# region clearConsoleScreen
if platform.system() == "Linux":
    def clearConsoleScreen():
        os.system("clear")
elif platform.system() == "Windows":
    def clearConsoleScreen():
        os.system("powershell clear")
else:
    def clearConsoleScreen():
        pass


# endregion

#region curses
class DummyCurses:

    def initscr(self):
        class DummyScreen:
            def getch(self):
                return 1

            def keypad(self, b=False):
                pass

        return DummyScreen()

    def noecho(self):
        pass

    def cbreak(self):
        pass

    KEY_UP = 0
    KEY_DOWN = 1

    def nocbreak(self):
        pass

    def echo(self):
        pass

    def endwin(self):
        pass


try:
    import curses
except ModuleNotFoundError:
    print("CONSOLE INPUT WILL NOT WORK, because 'curses' could not be imported.")
    curses = DummyCurses()

#endregion


@atexit.register
def OnExit():
    print("Cleaning up GPIO...")
    GPIO.cleanup()


if __name__ == "__main__":

    while True:
        i = input("Teste \n (0) Schalter \n (1) Lagesensor \n (2) Akkustand-Anzeige? \n (3) Potentiometer-Voltmeter ")

        if i == "0":
            SchalterTest()
        elif i == "1":
            Lagesensor_Test()
        elif i == "2":

            print(f"Gemeldete Spannungen: {Akkumesser.rawVoltages()}")
            print("Spannungen der Akkuzellen:", Akkumesser.cellVoltages())
            print(f"Es sollte je zwischen {Akkumesser.minSingle_V} und {Akkumesser.maxSingle_V} V liegen.")
        elif i == "3":
            PotentiometerTest()
     