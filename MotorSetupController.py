from Steuerungen import InternetSteuerung, Steuerung
import json
from pathlib import Path
import os
import datetime

CONFIGS_PATH = Path(__file__).parent / 'MotorConfigs' 
ACTIVE_SETTINGS_PATH = CONFIGS_PATH / 'active.json'
STANDARD_SETTINGS_PATH = CONFIGS_PATH  / 'default.json'

class MotorSetupController:
    def __init__(self, cls=InternetSteuerung, log=print):
        global ACTIVE_SETTINGS_PATH
        # assert issubclass(cls, Steuerung)
        if not ACTIVE_SETTINGS_PATH.is_file():
            if STANDARD_SETTINGS_PATH.is_file():
                os.symlink(STANDARD_SETTINGS_PATH, ACTIVE_SETTINGS_PATH)
                # ACTIVE_SETTINGS_PATH = STANDARD_SETTINGS_PATH
            else:
                raise Exception(f"Active and standard settings paths are broken: {ACTIVE_SETTINGS_PATH}, {STANDARD_SETTINGS_PATH}")
        settingsString = open(ACTIVE_SETTINGS_PATH, encoding="utf8").read()
        self.newDict = json.loads(settingsString)
        self.currentDict = json.loads(settingsString)
            
        self.current = cls(initializeMotors=self.newDict)
        self.cls = cls
        self.log = log

    def reloadWithNewConfig(self, config = None, force: bool = False):        
        self.current.stop()
        if config is not None:
            self.updateDict(config)
        try:
            newSteuerung = self.cls(initializeMotors=self.newDict)
        except Exception as e:
            self.log(f"New Steuerung could not be setup properly with the transmitted motor config. You can force it. Exception: {e}")
            # try:
            #     self.reset(force = True)
            # except:
            #     self.log("ERROR ALSO WHEN RESETTING")
            # return
            if not force: return False
        self.currentDict = self.newDict
        self.current = newSteuerung
        try:
            self.current.schreiben("CLOSING DUE TO UPDATED MOTOR CONFIG")
            self.current.quit()
        except Exception as e:
            self.log("Old Steuerung could not be stopped properly.  Exception: " + e)# You can force it.
            # if not force:
            #     return
        return True

    def updateConfig(self, path: Path = ACTIVE_SETTINGS_PATH):
        self.newDict = json.loads(open(path), encoding="utf8").read()

        
    def load(self, newDict: dict, force):
        if not self.reloadWithNewConfig(force=force):
            return
        self.current.schreiben("RESTARTED WITH NEW MOTOR CONFIG. ")
        self.current.schreiben("New config: " + str(newDict), 3)
        newPath = CONFIGS_PATH / datetime.datetime.now().strftime('Config %Y.%m.%d_%H_%M_%S.json')
        json.dump(self.newDict, newPath.open('w', encoding='utf8'))
        os.remove(ACTIVE_SETTINGS_PATH)
        os.symlink(newPath, ACTIVE_SETTINGS_PATH)
        self.log(f"Successfully set up new {self.cls.__name__} with the transmitted motor config!")

    def reset(self, force: bool = False):
        self.updateConfig(STANDARD_SETTINGS_PATH)
        if self.reloadWithNewConfig(force=force):
            self.current.schreiben("RESTARTED WITH DEFAULT MOTOR CONFIG. ")
            self.current.schreiben("Default config: " + str(self.newDict), 3)
            os.remove(ACTIVE_SETTINGS_PATH)
            os.symlink(STANDARD_SETTINGS_PATH, ACTIVE_SETTINGS_PATH)

    def updateDict(self, newDict):
        # TODO Types are missing
        for key in newDict:
            c = newDict[key]
            assert isinstance(c, dict)
            if not key in self.newDict:
                self.newDict[key] = {}
            for k in c:
                try:
                    self.newDict[key][k] = float(c[k])
                except:
                    self.newDict[key][k] = c[k]

            