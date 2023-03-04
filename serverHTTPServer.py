#!/usr/bin/python3
import json
import jsonpickle
import time
import click
from http.server import BaseHTTPRequestHandler, HTTPServer#, ThreadingHTTPServer

from MotorSetupController import MotorSetupController
import sys
print(sys.executable)
HOST = "127.0.0.1"  # Standard loopback interface address (localhost)
PORT = 6767  # Port to listen on (non-privileged ports are > 1023)

currentReply = ""
def addToCurrentReply(text):
    global currentReply
    currentReply += text

motorSetupController = None


def handleMotorChange(obj, force = False):
    global currentReply
    currentReply = ""

    if not isinstance(obj, dict):
        return "The transmitted data for the new Motor config was not interpreted as a dict. Transmit json data that contains a single jso."

    motorSetupController.load(obj, force=force)
    x = currentReply
    currentReply = ""
    return currentReply


class HandleRequests(BaseHTTPRequestHandler):
    def handleJsonRequest(self, function):
        begin = time.time()
        try:
            self._set_headers("json")
        except Exception as e:
            motorSetupController.current.schreiben(str(e))
        # keys of self.headers: ['Content-Length', 'Content-Type', 'Host', 'Connection', 'Cache-Control']
        if self.headers["Content-Type"].find("text/json") < 0:
            motorSetupController.current.schreiben(f"wrong content Type: {self.headers['Content-Type']}", 1)
            return
        # ohne den Parameter sollte er bis zum Ende lesen, aber er wartet darauf, bis alle timeouts abgelaufen sind
        contentLength = (int(self.headers["Content-Length"]) if "Content-Length" in self.headers else -1)
        content = self.rfile.read(contentLength).decode(encoding="utf-8")

        try:
            contentData = jsonpickle.decode(content)
        except json.decoder.JSONDecodeError:
            contentData = content

        #############################
        reply = function(contentData)
        #############################
        # motorSetupController.current.log("My reply:", reply)
        try:
            self.wfile.write(bytes(jsonpickle.encode(reply), "utf-8"))
        except BrokenPipeError:
            motorSetupController.current.schreiben(f"Abgelaufene Verbindung, meine Antwort wäre gewesen: {reply}", 2)
        timeSinceBegin = time.time() - begin
        if timeSinceBegin > 0.03:
            motorSetupController.current.schreiben(f"Very long calculation: {timeSinceBegin} s.", 1)
            
            
    def _set_headers(self, headerType="html"):
        self.send_response(200)
        self.send_header('Content-Type', 'text/' + headerType)
        self.end_headers()

    def do_GET(self):
        #self._set_headers("html")
        ## motorSetupController.current.log("Got a GET request")
        #self.wfile.write(
        #    b"<!DOCTYPE html><html><body><h1>Tubemarine-Server</h1><p>This server is made to handle POST requests with Content-Type json. It should be a dictionary with the name of registered motors as keys and their new value as number</p></body></html>")

        self._set_headers("json")
        self.wfile.write(bytes(jsonpickle.encode(motorSetupController.currentJSON), "utf-8"))


    def do_POST(self):  # when POST request reaches server this is called #asynchronously
        # motorSetupController.current.log("do_POST called")
        def handle(d):
            message = d.get('message','')
            if message == 'GET_MOTOR_SETTINGS':
                d.pop('message')
                return motorSetupController.currentJSON
            if message == 'SET_MOTOR_SETTINGS':
                d.pop('message')
                return handleMotorChange(d, False)
            return motorSetupController.current.onReceive(d)

        self.handleJsonRequest(lambda data: handle(convert(data)))

    def do_PUT(self):
        self.handleJsonRequest(lambda data: handleMotorChange(convert(data), False))

    def do_DELETE(self):
        self.handleJsonRequest(lambda data: handleMotorChange(convert(data), True))

def convert(rawData):                
    if isinstance(rawData, str):
        d = {'message': rawData}
    elif isinstance(rawData, dict):
        d = rawData
    else:
        d = {a: getattr(rawData, a) for a in dir(rawData) if
            not a.startswith('__') and not callable(getattr(rawData, a))}
    return d

@click.command()
@click.option("--log-level","--loglevel","-L","-l", default=6)
@click.option('--sleep', '-s', default=0)
def run(log_level=6, sleep=0):
    time.sleep(sleep)
    global motorSetupController
    motorSetupController = MotorSetupController(log=addToCurrentReply)
    motorSetupController.current.loglevel = log_level
    try:
        # Threading
        HTTPServer((HOST, PORT), HandleRequests).serve_forever()
    except KeyboardInterrupt:
        print("Closed by KeyboardInterrupt")
        if motorSetupController and motorSetupController.current:
            motorSetupController.current.stopAndQuit()


if __name__ == "__main__":
    run()
