# Tubemarine_Server
The code to be run on the Raspberry Pi inside the Tubemarine (our home-built Tubular submarine).
This can be remote controlled with 
https://github.com/p4jo/Tubemarine_Controller (as of yet not public -- will come sooner or later)

## Installation
Replace `python3` with a working python installation (I think >=3.7 is required)
```
cd /home/pi
clone https://github.com/p4jo/Tubemarine_Server.git
cd Tubemarine_Server
python3 -m venv .venv
.venv/bin/python3 -m pip install -r requirements.txt
```
### Test
Running `Steuerung.py` starts a console controller and allows you to test the motors
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
In `MotorConfigurations`. To see how it works, see `MotorSetupController.py` 
