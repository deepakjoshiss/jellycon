import os
import traceback
import xbmcplugin
import xbmcgui
import xbmcaddon
import xbmc

from .lazylogger import LazyLogger

log = LazyLogger(__name__)

from .utils import translate_path

MONITOR = xbmc.Monitor()
THEME = 'default'
RES = '720p'

__addon__ = xbmcaddon.Addon()
__addondir__ = translate_path(__addon__.getAddonInfo('profile'))
__cwd__ = __addon__.getAddonInfo('path')
PLUGINPATH = translate_path(os.path.join(__cwd__))
addon_id = __addon__.getAddonInfo('id')


class BaseWindow(xbmcgui.WindowXML):

    def __init__(self, *args, **kwargs):
        self._winID = ''
        self.started = False
        self.isOpen = False
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

    def onInit(self):
        log.info(">>>>>>>>>>>> Searchscreen onInit {} {}".format(self.started, xbmcgui.getCurrentWindowId()))
        self._winID = xbmcgui.getCurrentWindowDialogId()
        if self.started:
            self.onReInit()
        else:
            self.started = True
            self.onFirstInit() 

    def onAction(self, action):
        try:
            if action in (xbmcgui.ACTION_PREVIOUS_MENU, xbmcgui.ACTION_NAV_BACK):
                self.close()
                return
        except:
            traceback.print_exc()

        xbmcgui.WindowXML.onAction(self, action)

    @classmethod
    def create(cls, **kwargs):
        window = cls(cls.xmlFile, PLUGINPATH, THEME, RES, **kwargs)
        return window
    
    @classmethod
    def showWindow(cls, **kwargs):
        window = cls.create(**kwargs)
        window.show()
        return window
    
    def show(self):
        self._closing = False
        #self.isOpen = True
        xbmcgui.WindowXML.show(self)
        log.info(">>>>>>>>>>>> Searchscreen {}".format(xbmcgui.getCurrentWindowId()))
        self.isOpen = xbmcgui.getCurrentWindowId() >= 13000

    def onFirstInit(self):
        pass

    def onReInit(self):
        pass

    def close(self):
        self._closing = True
        log.info(">>>>>>>>>>>> Searchscreen closing {}".format(xbmcgui.getCurrentWindowId()))
        xbmcgui.WindowXML.close(self)
        self.isOpen = False
    
    def isWindowOpen(self):
        return self.isOpen

class BaseDialog(xbmcgui.WindowXMLDialog):

    def __init__(self, *args, **kwargs):
        xbmcgui.WindowXMLDialog.__init__(self, *args, **kwargs)

    def onAction(self, action):
        xbmcgui.WindowXMLDialog.onAction(self, action)

    @classmethod
    def create(cls, **kwargs):
        window = cls(cls.xmlFile, PLUGINPATH, THEME, RES, **kwargs)
        return window
    
    @classmethod
    def openModal(cls, **kwargs):
        window = cls.create(**kwargs)
        window.doModal()
        return window
    
    def doModal(self):
        self.isOpen = True
        try:
            super().doModal()
        except SystemExit:
            pass
        # self.onClosed()
        self.isOpen = False

    def doClose(self):
        self._closing = True
        self.close()
        self.isOpen = False


class SafeControlEdit(object):
    CHARS_LOWER = 'abcdefghijklmnopqrstuvwxyz'
    CHARS_UPPER = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    CHARS_NUMBERS = '0123456789'
    CURSOR = '[COLOR $VAR[ColorHighlight]]|[/COLOR]'

    def __init__(self, control_id, label_id, window, key_callback=None, grab_focus=False):
        self.controlID = control_id
        self.labelID = label_id
        self._win = window
        self._keyCallback = key_callback
        self.grabFocus = grab_focus
        self._text = ''
        self._compatibleMode = False
        self.setup()

    def setup(self):
        self._labelControl = self._win.getControl(self.labelID)
        self._winOnAction = self._win.onAction
        self._win.onAction = self.onAction
        self.updateLabel()

    def setCompatibleMode(self, on):
        self._compatibleMode = on

    def onAction(self, action):
        # log.info(">>>>>>>>> Searchscreen action {}".format(self._win.getControl(1001).getLabel()))
        try:
            controlID = self._win.getFocusId()
            if controlID == self.controlID:
                if self.processAction(action.getId()):
                    return
            elif self.grabFocus:
                if self.processOffControlAction(action.getButtonCode()):
                    self._win.setFocusId(self.controlID)
                    return
        except:
            log.error('Action Error')

        self._winOnAction(action)

    def processAction(self, action_id):
        if not self._compatibleMode:
            oldVal = self._text
            self._text = self._win.getControl(self.controlID).getText()

            if self._keyCallback:
                self._keyCallback(action_id, oldVal, self._text)

            self.updateLabel()

            return True
        oldVal = self.getText()

        if 61793 <= action_id <= 61818:  # Lowercase
            self.processChar(self.CHARS_LOWER[action_id - 61793])
        elif 61761 <= action_id <= 61786:  # Uppercase
            self.processChar(self.CHARS_UPPER[action_id - 61761])
        elif 61744 <= action_id <= 61753:
            self.processChar(self.CHARS_NUMBERS[action_id - 61744])
        elif action_id == 61728:  # Space
            self.processChar(' ')
        elif action_id == 61448:
            self.delete()
        else:
            return False

        if self._keyCallback:
            self._keyCallback(action_id, oldVal, self.getText())

        return True

    def processOffControlAction(self, action_id):
        oldVal = self.getText() if self._compatibleMode else self._text
        if 61505 <= action_id <= 61530:  # Lowercase
            self.processChar(self.CHARS_LOWER[action_id - 61505])
        elif 192577 <= action_id <= 192602:  # Uppercase
            self.processChar(self.CHARS_UPPER[action_id - 192577])
        elif 61488 <= action_id <= 61497:
            self.processChar(self.CHARS_NUMBERS[action_id - 61488])
        elif 61552 <= action_id <= 61561:
            self.processChar(self.CHARS_NUMBERS[action_id - 61552])
        elif action_id == 61472:  # Space
            self.processChar(' ')
        else:
            return False

        if self._keyCallback:
            self._keyCallback(action_id, oldVal, self.getText())

        return True

    def _setText(self, text):
        self._text = text

        if not self._compatibleMode:
            self._win.getControl(self.controlID).setText(text)
        self.updateLabel()

    def _getText(self):
        if not self._compatibleMode and self._win.getFocusId() == self.controlID:
            return self._win.getControl(self.controlID).getText()
        else:
            return self._text

    def updateLabel(self):
        self._labelControl.setLabel(self._getText() + self.CURSOR)

    def processChar(self, char):
        self._setText(self.getText() + char)

    def setText(self, text):
        self._setText(text)

    def getText(self):
        return self._getText()

    def append(self, text):
        self._setText(self.getText() + text)

    def delete(self):
        self._setText(self.getText()[:-1])
