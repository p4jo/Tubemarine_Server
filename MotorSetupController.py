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
                ACTIVE_SETTINGS_PATH = STANDARD_SETTINGS_PATH
            else:
                raise Exception(f"Active and standard settings paths are broken: {ACTIVE_SETTINGS_PATH}, {STANDARD_SETTINGS_PATH}")
        self.currentDict = json.loads(open(ACTIVE_SETTINGS_PATH, encoding="utf8").read())
            
        self.current = cls(initializeMotors=self.currentDict)
        self.cls = cls
        self.log = log

    def reloadWithNewConfig(self, force: bool = False):        
        self.current.stop()
        try:
            newSteuerung = self.cls(initializeMotors=self.currentDict)
        except Exception as e:
            self.log(f"New Steuerung could not be setup properly with the transmitted motor config. You can force it. Exception: {e}")
            # try:
            #     self.reset(force = True)
            # except:
            #     self.log("ERROR ALSO WHEN RESETTING")
            # return
            if not force: return False

        try:
            self.current.schreiben("CLOSING DUE TO UPDATED MOTOR CONFIG")
            self.current.quit()
        except Exception as e:
            self.log("Old Steuerung could not be stopped properly.  Exception: " + e)# You can force it.
            # if not force:
            #     return
        self.current = newSteuerung
        return True

        
    def load(self, newDict: dict, force):
        self._updateDict(newDict) # TODO Types are missing
        if not self.reloadWithNewConfig(force=force):
            return
        self.current.schreiben("RESTARTED WITH NEW MOTOR CONFIG. ")
        self.current.schreiben("New config: " + str(newDict), 3)
        newPath = CONFIGS_PATH / datetime.datetime.now().strftime('Config %Y.%m.%d_%H_%M_%S.json')
        json.dump(self.currentDict, newPath.open('w', encoding='utf8'))
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
            assert isinstance(c, dict)
            if not key in self.currentDict:
                self.currentDict[key] = {}
            for k in c:
                try:
                    self.currentDict[key][k] = float(c[k])
                except:
                    self.currentDict[key][k] = c[k]

            