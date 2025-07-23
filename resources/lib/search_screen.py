import threading
import time
import traceback
from urllib.parse import urlencode
import xbmc
import xbmcgui

from resources.lib.kodi_utils import HomeWindow

from .jellyfin import api
from resources.lib.jsonrpc import JsonRpc
from resources.lib.utils import get_default_filters, get_jellyfin_url

from .lazylogger import LazyLogger
from .kodigui import MONITOR, BaseWindow, SafeControlEdit
from resources.lib import kodigui

log = LazyLogger(__name__)

class SearchScreen(BaseWindow):
    xmlFile = 'Custom_1161_SearchScreen.xml'
    winId = 1161
    letters = 'abcdefghijklmnopqrstuvwxyz1234567890 '
    num_columns = 6
    num_rows = 6
    start_id = 1001
    edit_id = 650
    test_count = 0
    hub_list_id = 8500
    hub_movie_id = 8501
    hub_all_id = 8510

    edit = None
    home_window = HomeWindow()

    def __init__(self, *args, **kwargs):
        log.info(">>>>>>>> SearchSecreen")
        BaseWindow.__init__(self, *args, **kwargs)
        self.resultsThread = None
        self.updateResultsTimeout = 0
        self.isActive = True
        log.info(">>>>>>>> SearchSecreen Loaded")
    
    def onFirstInit(self):
        self.initViews()
    
    def onReInit(self):
        pass
    
    def initViews(self):
        self.initEdit()
        self.initLetters()
    
    def onAction(self, action):
        try:
            if action in (xbmcgui.ACTION_NAV_BACK, xbmcgui.ACTION_PREVIOUS_MENU):
                self.isActive = False
        except:
            log.error('Error on Action {}'.format(action))

        BaseWindow.onAction(self, action)

    def onClick(self, controlID):
        log.debug('>>>>>>>>> MediaInfoDialog: selected control {}'.format(controlID))
        if self.start_id <= controlID < 1037:
            self.letterClicked(controlID)
        elif controlID == 1063:
            self.deleteClicked()
        elif controlID == 1064:
            self.letterClicked(1037)
        elif controlID == 1062:
            self.clearClicked()

    def letterClicked(self, controlID):
        letter = self.letters[controlID - self.start_id]
        self.edit.append(letter)
        self.updateQuery()
    
    def deleteClicked(self):
        self.edit.delete()
        self.updateQuery()
    
    def clearClicked(self):
        self.edit.setText('')
        self.updateQuery()
    
    def updateFromEdit(self, actionID, oldVal, newVal):
        if actionID == xbmcgui.ACTION_PREVIOUS_MENU:
            self.isActive = False
            self.doClose()
            return

        self.updateQuery()

    def updateQuery(self):
        self.updateResults()

    def updateResults(self):
        self.updateResultsTimeout = time.time() + 1
        if not self.resultsThread or not self.resultsThread.is_alive():
            self.resultsThread = threading.Thread(target=self._updateResults, name='search.update')
            self.resultsThread.start()

    def _updateResults(self):
        while time.time() < self.updateResultsTimeout and not MONITOR.waitForAbort(0.2):
            pass
        
        self.test_count+=1
        log.info(">>>>>>>>> result thread {} {}".format(self.test_count, self.edit.getText()))
        self.getControl(652).setLabel(self.edit.getText())
        self._reallyUpdateResults()
    
    def _reallyUpdateResults(self):
        query = self.edit.getText()
        if query and query != self.home_window.get_property('currentsearchquery'):
            self.home_window.set_property('currentsearchquery', "{}".format(query))
            url_params = {
                "searchTerm": query,
                "IncludePeople": False,
                "IncludeMedia": True,
                "IncludeGenres": False,
                "IncludeStudios": False,
                "IncludeArtists": False,
                "Limit": 10,
                "Fields": get_default_filters(),
                "Recursive": True,
                "EnableTotalRecordCount": False,
                "ExcludeItemTypes": "Movie,Series,Episode",
                "ImageTypeLimit": 1
            }
            url_path = "/Users/{}/Items".format(api.user_id)
            search_url = get_jellyfin_url(url_path, url_params)

            action_params = {
                "mode": 'GET_CONTENT',
                "media_type": 'mixed',
                "url": search_url
            }
            str_params = urlencode(action_params)
            action_url = "plugin://{}/?{}".format(kodigui.addon_id, str_params)
            
            self.home_window.set_property('togglevisible', '1')

            self.home_window.set_property('currentsearchpath', action_url)
            url_params["IncludeItemTypes"] = "Movie,Series"
            url_params["ExcludeItemTypes"] = None
            search_url = get_jellyfin_url(url_path, url_params)
            action_params = {
                "mode": 'GET_CONTENT',
                "media_type": 'Movies',
                "url": search_url
            }
            str_params = urlencode(action_params)
            action_url = "plugin://{}/?{}".format(kodigui.addon_id, str_params)
            self.home_window.set_property('moviesearchpath', action_url)

            url_params["IncludeItemTypes"] = "Episode"
            url_params["ExcludeItemTypes"] = None
            search_url = get_jellyfin_url(url_path, url_params)
            action_params = {
                "mode": 'GET_CONTENT',
                "media_type": 'Movies',
                "url": search_url
            }
            str_params = urlencode(action_params)
            action_url = "plugin://{}/?{}".format(kodigui.addon_id, str_params)
            self.home_window.set_property('episodesearchpath', action_url)

            threading.Timer(0.2, self.clearVisible).start()
            # params = {
            #     "directory": "%s" % action_url,
            #     "media": "files",
            #     "properties": ["title", "file", "thumbnail",
            #                     "episode", "showtitle", "season", "trailer", "art"]
            # }

            # results = JsonRpc("Files.GetDirectory").execute(params)
            # files = results.get('result', {}).get('files', [])
            # li = None
            # list_items = []
            # for file in files:
            #     li = xbmcgui.ListItem(translate_string(30314), offscreen=True)
            #     li.setProperty('menu_id', 'play')
            #     list_items.append(li)
            #     log.info(">>>>> Search results {}".format(file))

    def clearVisible(self):
        self.home_window.clear_property('togglevisible')

    def isConfirmed(self):
        return False
    # def onInit(self):

    def initEdit(self):
        if self.edit:
            self.edit.setup()
        else:    
            self.edit = SafeControlEdit(self.edit_id, 651, self, key_callback=self.updateFromEdit,
                                            grab_focus=True)

    def initLetters(self):
        control = None
        for i in range(self.num_rows * self.num_columns):
            try:
                control = self.getControl(self.start_id + i)
                if control:
                    control.setLabel(self.letters[i].upper())
                    
                    if i < (self.num_rows - 1) * self.num_columns:
                        control.controlDown(self.getControl(self.start_id + i + self.num_columns))
                    if i >= self.num_columns:
                        control.controlUp(self.getControl(self.start_id + i - self.num_columns))
                    else:
                        control.controlUp(self.getControl(self.edit_id))
            except:
                traceback.print_exc()
