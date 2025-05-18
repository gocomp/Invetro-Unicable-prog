from enigma import eDVBDiseqcCommand, eDVBResourceManager, iDVBFrontend
from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.FileList import FileList
from Components.Label import Label
from Components.ActionMap import ActionMap
from Screens.InfoBar import InfoBar
from time import sleep
from os import path

class DiseqcSender(Screen):
    skin = """
        <screen position="center,center" size="760,400" title="Send DiSEqC Binary">
            <widget name="filelist" position="10,10" size="540,340" scrollbarMode="showOnDemand" />
            <widget name="key_red" position="10,360" size="130,30" font="Regular;20" valign="center" halign="center" backgroundColor="#9f1313" foregroundColor="white" />
        </screen>"""

    def __init__(self, session):
        Screen.__init__(self, session)
        self.setTitle("Send INVERTO Unicable dsq File")
        self.session = session

        self.filelist = FileList("/tmp/", matchingPattern=".*\.dsq$")
        self["filelist"] = self.filelist
        self["key_red"] = Label("Cancel")
        self["key_green"] = Label("Ok")
        self.oldref = session.nav.getCurrentlyPlayingServiceReference()
        self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
            "ok": self.sendFile,
            "green": self.sendFile,
            "cancel": self.close,
            "red": self.close,
        }, -1)

        self.frontend = None
        self.raw_channel = None

    def openFrontend(self):
        def tryFrontend():
            res_mgr = eDVBResourceManager.getInstance()
            if not res_mgr:
                return False
            self.raw_channel = res_mgr.allocateRawChannel(0)
            if not self.raw_channel:
                return False
            self.frontend = self.raw_channel.getFrontend()
            return self.frontend is not None

        if tryFrontend():
            return True


        try:
            self.oldref = self.session.nav.getCurrentlyPlayingServiceReference()
            self.session.nav.stopService()
        except Exception as e:
            print("[DEBUG] nav.stopService error:", str(e))

        sleep(1)
        if tryFrontend():
            return True


        try:
            infoBar = InfoBar.instance
            if hasattr(infoBar, "pipAvailable") and infoBar.pipAvailable():
                pipService = infoBar.session.pip.pipservice
                infoBar.session.pipshown = False
                del infoBar.session.pip
        except Exception as e:
            print("[DEBUG] PiP disable error:", str(e))

        sleep(1)
        return tryFrontend()
        
    def __onClose(self):
        
        if self.frontend:
            self.frontend = None
            del self.raw_channel
            self.session.nav.playService(self.oldref)
        self.close()
        
    def close(self):
        
        if self.frontend:
            self.frontend = None
            del self.raw_channel
            self.session.nav.playService(self.oldref)         
        Screen.close(self)
                
    def sendFile(self):
        filepath = self.filelist.getCurrent()[0]
        
        try:
            with open(
               self.filelist.getCurrentDirectory() + self.filelist.getFilename(), "rb"
            ) as f:
               lines = f.readlines()

        except Exception as e:
            self.session.open(MessageBox, "Failed to read file:", MessageBox.TYPE_ERROR)
            return

        if not self.openFrontend():
            self.session.open(MessageBox, "Tuner unavailable (even after reset).", MessageBox.TYPE_ERROR)
            return

        self.frontend.setTone(iDVBFrontend.toneOff)
        sleep(0.015)

        for line in lines:
            line = line.strip().replace(" ", "")
            if not line:
                continue
            try:
                print("[DEBUG] kuldom:"+line)
                cmd = eDVBDiseqcCommand()
                cmd.setCommandString(line)
                self.frontend.sendDiseqc(cmd)
                if line.upper() == "E03160":
                    sleep(0.05)
                    self.frontend.sendDiseqc(cmd)
                sleep(0.1)
            except Exception as e:
                self.session.open(MessageBox, "Sending failed:" , MessageBox.TYPE_ERROR)
                return
        self.session.open(MessageBox, "All DiSEqC commands sent successfully! Please restart box!", MessageBox.TYPE_INFO)


def main(session, **kwargs):
    session.open(DiseqcSender)

def Plugins(**kwargs):
    return [PluginDescriptor(
        name="INVERTO Unicable Programmer",
        description="Send INVERTO Unicable configuration file (.dsq) from /tmp to program INVERTO Unicable devices ",
        where=PluginDescriptor.WHERE_PLUGINMENU,
        fnc=main,
    )]
