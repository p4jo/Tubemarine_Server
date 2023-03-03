import datetime
import time

from SDL_Pi_INA3221 import SDL_Pi_INA3221

# Main Program
ADDRESS = 0x42

# filename = time.strftime("%Y-%m-%d%H:%M:%SRTCTest") + ".txt"
startTime = datetime.datetime.utcnow()
ina3221 = SDL_Pi_INA3221(addr = ADDRESS)


def printAllVoltages(name, channel):
    busVoltage_V = ina3221.getBusVoltage_V(channel)
    # shuntVoltage_mV = ina3221.getShuntVoltage_mV(channel)
    # minus is to get the "sense" right.   - means the battery is charging, + that it is discharging
    current_mA = ina3221.getCurrent_mA(channel)
    # loadVoltage_V = busVoltage_V + (shuntVoltage_mV / 1000)

    print(name, "Bus Voltage: %3.2f V " % busVoltage_V)
    # print(name, "Shunt Voltage: %3.2f mV " % shuntVoltage_mV)
    # print(name, "Load Voltage:  %3.2f V" % loadVoltage_V)
    print(name, "Current:  %3.2f mA" % current_mA)
    print()


if __name__ == '__main__':
    print("Program Started at:" + time.strftime("%Y-%m-%d %H:%M:%S"))
    print("Address %x" % ADDRESS)

    while True:
        print("------------------------------")
        printAllVoltages("Channel 1", 1)
        printAllVoltages("Channel 2", 2)
        printAllVoltages("Channel 3", 3)
        time.sleep(2.0)
