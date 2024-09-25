import xbmc
import xbmcgui

from .jellyfin import api
from .lazylogger import LazyLogger

log = LazyLogger(__name__)

SKIP_KEYS = {
    'DvVersionMajor',
    'DvVersionMinor',
    'DisplayTitle',
    'VideoRange',
    'BlPresentFlag',
    'DvBlSignalCompatibilityId',
    'isAVC',
    'LocalizedDefault',
    'LocalizedExternal',
    'LocalizedHearingImpaired',
    'LocalizedForced',
    'LocalizedUndefined',
}


class MediaInfoDialog(xbmcgui.WindowXMLDialog):

    item_id = None
    listControl = None
    titleControl = None
    fileInfoControl = None
    infoControl = None
    infoControl2 = None
    itemData = None
    mediaStreams = None

    def __init__(self, *args, **kwargs):
        log.debug("MediaInfoDialog: __init__")
        xbmcgui.WindowXML.__init__(self, *args, **kwargs)

    def onInit(self):
        self.action_exitkeys_id = [10, 13]

        self.listControl = self.getControl(3000)
        self.titleControl = self.getControl(3100)
        self.fileInfoControl = self.getControl(3101)
        self.infoControl = self.getControl(3111)
        self.infoControl2 = self.getControl(3112)

        url = "/Users/{}/Items/{}?format=json".format(api.user_id, self.item_id)
        self.itemData = api.get(url)
        self.titleControl.setLabel(self.itemData.get('Name', 'Unknown'))
        self.mediaStreams = self.itemData.get('MediaStreams', [])
        mediaSource = self.itemData.get('MediaSources', [])[0]
        self.fileInfoControl.setLabel("Container: [LIGHT]{}[/LIGHT]    Size: [LIGHT]{} MB[/LIGHT]    Date Added: [LIGHT]{}[/LIGHT]".format(
            mediaSource.get('Container'),
            int(int(mediaSource.get('Size')) / 1000000),
            self.itemData.get('DateCreated')
        ))

        log.debug("MediaInfoDialog item details: {0}".format(self.itemData.get('Id', '')))

        list_items = []
        li = None
        for index, stream in enumerate(self.mediaStreams):
            # log.info('>>>>>>>>> MediaInfoDialog: adding {}'.format(stream.get('DisplayTitle', ' lala')))
            li = xbmcgui.ListItem(stream.get('Type', '') + ' ' + stream.get('DisplayTitle', ''), offscreen=True)
            li.setProperty('StreamIndex', str(index))
            if index == 0:
                self.set_media_info(index, li)
            list_items.append(li)

        self.listControl.addItems(list_items)
        self.setFocus(self.listControl)

    def set_media_info(self, index, list_item):
        stream = self.mediaStreams[index]
        stream_info = ''
        stream_info2 = ''
        temp_str = ''
        count = 0
        for key in stream:
            if key in SKIP_KEYS:
                continue
            temp_str = "{} [LIGHT]> {}[/LIGHT][CR]".format(key, str(stream.get(key)))
            if (count < 18):
                stream_info += temp_str
            else:
                stream_info2 += temp_str
            count += 1
            # log.info('>>>>>>>>> MediaInfoDialog: stream loop {} >>>>>> {}'.format(key, stream.get(key)))
        list_item.setProperty('StreamInfo', stream_info)
        list_item.setProperty('StreamInfo2', stream_info2)

    def onFocus(self, control_id):
        log.debug('>>>>>>>>> MediaInfoDialog: focused control {} >>>> {}'.format(control_id))
        pass

    # def doAction(self, action_id):
    #     pass

    def onMessage(self, message):
        log.debug("MediaInfoDialog: onMessage: {0}".format(message))

    def onAction(self, action):
        if action.getId() == 10:  # ACTION_PREVIOUS_MENU
            self.close()
        elif action.getId() == 92:  # ACTION_NAV_BACK
            self.close()

        # For later use
        # selected_action = self.listControl.getSelectedItem()
        # index = int(selected_action.getProperty('StreamIndex'))
        # log.info('>>>>>>>>> MediaInfoDialog: action captured {} {}'.format(action.getId(), index))

    def onClick(self, control_id):
        log.debug('>>>>>>>>> MediaInfoDialog: selected control {}'.format(control_id))
        if control_id == 3000:
            selected_action = self.listControl.getSelectedItem()
            index = int(selected_action.getProperty('StreamIndex'))
            self.set_media_info(index, selected_action)
            log.debug('>>>>>>>>> MediaInfoDialog: setting stram info {}'.format(index))
            pass

    def setItemId(self, item_id):
        self.item_id = item_id

    def getItemId(self):
        return self.item_id
