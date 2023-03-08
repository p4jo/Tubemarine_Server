# Tubemarine_Server
The code to be run on the Raspberry Pi inside the Tubemarine (our home-built Tubular submarine).
This can be remote controlled with 
https://github.com/p4jo/Tubemarine_Controller (as of yet not public -- will come sooner or later)

## Installation
```
cd /home/pi
clone https://github.com/p4jo/Tubemarine_Server.git
cd Tubemarine_Server
python3 -m venv .venv
.venv/bin/python3 -m pip install -r requirements.txt
```
You may want to replace `python3` with a working python installation (I think >=3.7 is required)
### Test
Running `Steuerung.py` starts a console controller and allows you to test the motors.
The `serverHTTPServer.py` contains the server-side application for the Tubemarine_Controller. By default it runs on port `6767`.
```
cd /home/pi/Tubemarine_Server
.venv/bin/python3 Steuerung.py
.venv/bin/python3 serverHTTPServer.py -l 15
```


### Autostart
The service `U-Boot.service` autostarts the serverHTTPServer.py with 60 s wait before it starts (so that you can still stop it when it malfunctions on startup)
```
cd /etc/systemd/system
sudo ln /home/pi/Tubemarine_Server/U-Boot.service
sudo systemctl enable U-Boot
sudo systemctl start U-Boot
```
Logs: 
```
journalctl -f -u U-Boot
tail -f /home/pi/Internetsteuerung.log
```

## Configuration
In `MotorConfigurations`. To see how it works, see `Motoren.py > loadMotorConfig` and the subclasses of `Motor`.
`active.json` should be a symlink to the currently active one and `default.json` can (in theory) be used after reset.

## Structure of the program
### Classes
* Steuerung

    The base class for classes that control motors and handle messages (`steuerung.schreiben` is a log function). It can be initialized with a dict of the type in `MotorConfigs`.
    * InternetSteuerung

        The `Steuerung` that runs headless and returns everything from its `onReceive` method
    * KonsolenSteuerung

        The `Steuerung` that can be used in the terminal (e.g. per SSH). Useful for testing.

* Motor
  
## TODO
* Visualisierung von Sensordaten
* Regelung