import jsonpickle
from http.server import BaseHTTPRequestHandler, HTTPServer

class HandleRequests(BaseHTTPRequestHandler):
    def handleJsonRequest(self):
        try:
            self._set_headers("json")
        except Exception as e:
            logFunction(str(e))
        # keys of self.headers: ['Content-Length', 'Content-Type', 'Host', 'Connection', 'Cache-Control']
        if self.headers["Content-Type"].find("text/json") < 0:
            logFunction(f"wrong content Type: {self.headers['Content-Type']}", 1)
            return
        # ohne den Parameter sollte er bis zum Ende lesen, aber er wartet darauf, bis alle timeouts abgelaufen sind
        contentLength = (int(self.headers["Content-Length"]) if "Content-Length" in self.headers else -1)
        content = self.rfile.read(contentLength).decode(encoding="utf-8")


        #############################
        reply = handleFunction(content)
        #############################
        # motorSetupController.current.log("My reply:", reply)
        try:
            reply_encoded = jsonpickle.encode(reply)
            self.wfile.write(bytes(reply_encoded, "utf-8"))
        except BrokenPipeError:
            logFunction(f"Abgelaufene Verbindung.", 4)
            logFunction(f"Meine Antwort wäre gewesen: {reply}", 10)
            
            
    def _set_headers(self, headerType="html"):
        self.send_response(200)
        self.send_header('Content-Type', 'text/' + headerType)
        self.end_headers()

    def do_GET(self):
        # self._set_headers("html")
        # # motorSetupController.current.log("Got a GET request")
        # self.wfile.write(
        #    b"<!DOCTYPE html><html><body><h1>Tubemarine-Server</h1><p>This server is made to handle POST requests with Content-Type json. It should be a dictionary with the name of registered motors as keys and their new value as number</p></body></html>")

    def do_POST(self):  # when POST request reaches server this is called #asynchronously
        self.handleJsonRequest()


logFunction = print
handleFunction = lambda text: None

def run_forever(port, handle_function = None, log_function = None):
    global logFunction, handleFunction
    if log_function is not None:
        logFunction = log_function
    if handle_function is not None:
        handleFunction = handle_function
    HTTPServer(("127.0.0.1", port), HandleRequests).serve_forever()
