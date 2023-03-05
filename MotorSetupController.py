from Steuerungen import InternetSteuerung
import json
from pathlib import Path
import os
import datetime

CONFIGS_PATH = Path(__file__).parent / 'MotorConfigs' 
ACTIVE_SETTINGS_PATH = CONFIGS_PATH / 'active.json'
STANDARD_SETTINGS_PATH = CONFIGS_PATH  / 'default.json'

class MotorSetupController:


    def __init__(self, cls=InternetSteuerung, log=print):
        # TODO check if is subclass of Steuerung
        self.currentDict = json.loads(open(ACTIVE_SETTINGS_PATH, encoding="utf8").read())
        self.current = cls(initializeMotors=self.currentDict)
        self.cls = cls
        self.log = log

    def reloadWithNewConfig(self, force: bool = False):        
        try:
            self.current.schreiben("CLOSING DUE TO UPDATED MOTOR CONFIG")
            self.current.stopAndQuit()
        except Exception as e:
            self.log("Old Steuerung could not be stopped properly. You can force it. Exception: " + e)
            if not force:
                return

        try:
            self.current = self.cls(initializeMotors=self.currentDict)
        except Exception as e:
            self.log(f"New Steuerung could not be setup properly with the transmitted motor config. You can force it. Exception: {e}")
            try:
                self.reset(force = True)
            except:
                self.log("ERROR ALSO WHEN RESETTING")
            return
        
    def load(self, newDict: dict, force):
        self._updateDict(newDict)
        self.reloadWithNewConfig(force=force)
        self.current.schreiben("RESTARTED WITH NEW MOTOR CONFIG. ")
        self.current.schreiben("New config: " + str(newDict), 3)
        newPath = CONFIGS_PATH / datetime.datetime.now().strftime('Config %Y.%m.%d_%H_%M_%S.json')
        json.dump(newDict, newPath)
        os.remove(ACTIVE_SETTINGS_PATH)
        os.symlink(newPath, ACTIVE_SETTINGS_PATH)
        self.log("Successfully set up new InternetSteuerung with the transmitted motor config!")

    def reset(self, force: bool = False):
        self.currentDict = json.loads(open(STANDARD_SETTINGS_PATH, encoding="utf8").read())
        self.reloadWithNewConfig()
        self.current.schreiben("RESTARTED WITH DEFAULT MOTOR CONFIG. ")
        self.current.schreiben("Default config: " + str(self.currentDict), 3)
        os.remove(ACTIVE_SETTINGS_PATH)
        os.symlink(STANDARD_SETTINGS_PATH, ACTIVE_SETTINGS_PATH)

    def _updateDict(self, newDict):
        for key in newDict:
            c = newDict[key]
            # if key not in self.currentDict:
            self.currentDict[key] = c
            