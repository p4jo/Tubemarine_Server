
import time

import click
import jsonpickle
from MotorSetupController import MotorSetupController
from timetest import timeTest
PORT = 6767  # Port to listen on (non-privileged ports are > 1023)

currentReply = ""
def addToCurrentReply(text):
    global currentReply
    currentReply += text

motorSetupController:MotorSetupController = None

@timeTest(log=lambda text: motorSetupController.current.schreiben(text, 4))
def handle(d):
    d = convert(d)
    message = d.get('message','')
    if message == 'GET_MOTOR_SETTINGS':
        d.pop('message')
        motorSetupController.current.schreiben('Loading current motor settings', 3)
        motorSetupController.current.schreiben('Current motor settings: ' + str(motorSetupController.currentDict), 5)
        return motorSetupController.currentDict
    if message == 'SET_MOTOR_SETTINGS':
        d.pop('message')
        return handleMotorChange(d, False)
    return motorSetupController.current.onReceive(d)

def convert(rawData: str):    
    try:
        rawData = jsonpickle.decode(rawData)
    except:
        pass

    if isinstance(rawData, str):
        d = {'message': rawData}
    elif isinstance(rawData, dict):
        d = rawData
    else:
        d = {a: getattr(rawData, a) for a in dir(rawData) if
            not a.startswith('__') and not callable(getattr(rawData, a))}
    return d

def handleMotorChange(obj, force = False):
    global currentReply
    currentReply = ""

    if not isinstance(obj, dict):
        return "The transmitted data for the new Motor config was not interpreted as a dict. Transmit json data that contains a single jso."

    motorSetupController.load(obj, force=force)
    return currentReply


@click.command()
@click.option("--log-level","--loglevel","-L","-l", default=6)
@click.option('--sleep', '-s', default=0)
@click.option('-http', is_flag=True)
def run(log_level=6, sleep=0, http):
    time.sleep(sleep)
    global motorSetupController
    motorSetupController = MotorSetupController(log=addToCurrentReply)
    motorSetupController.current.loglevel = log_level
    if http:
        from serverHTTPServer import run_forever
    else:
        from serverStreams import run_forever

    try:
        run_forever(PORT, motorSetupController.current.schreiben)
    except KeyboardInterrupt:
        print("Closed by KeyboardInterrupt")
        if motorSetupController and motorSetupController.current:
            motorSetupController.current.stopAndQuit()
        exit(0)

if __name__ == "__main__":
    run()
