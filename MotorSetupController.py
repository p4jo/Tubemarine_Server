from Steuerungen import InternetSteuerung
import json
from pathlib import Path

class MotorSetupController:

    standardSettingsPath = Path(__file__).parent / 'MotorConfigs' / 'default.json'

    def __init__(self, cls=InternetSteuerung, log=print):
        # TODO check if is subclass of Steuerung
        self.currentJSON = json.loads(open(self.standardSettingsPath, encoding="utf8").read())
        self.current = cls(initializeMotors=self.currentJSON)
        self.cls = cls
        self.log = log

    def load(self, motorJsonDict: dict, force):
        try:
            self.current.stopAndQuit()
        except Exception as e:
            self.log("Old Steuerung could not be stopped properly. You can force it. Exception: " + e)
            if not force:
                return
        try:
            self.currentJSON = motorJsonDict
            self.current = self.cls(initializeMotors=self.currentJSON)
        except Exception as e:
            self.log(f"New Steuerung could not be setup properly with the transmitted motor config. You can force it. Exception: {e}")
            return

        self.log("Successfully set up new InternetSteuerung with the transmitted motor config!")

