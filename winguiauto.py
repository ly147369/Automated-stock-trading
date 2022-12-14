# -*- encoding: utf8 -*-

import time
import struct
import win32api
import win32gui
import ctypes

import win32con
import commctrl

GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
VirtualAllocEx = ctypes.windll.kernel32.VirtualAllocEx
VirtualFreeEx = ctypes.windll.kernel32.VirtualFreeEx
OpenProcess = ctypes.windll.kernel32.OpenProcess
WriteProcessMemory = ctypes.windll.kernel32.WriteProcessMemory
ReadProcessMemory = ctypes.windll.kernel32.ReadProcessMemory


def _readListViewItems(hwnd, column_index=0):
    # Allocate virtual memory inside target process
    pid = ctypes.create_string_buffer(4)
    p_pid = ctypes.addressof(pid)
    GetWindowThreadProcessId(hwnd, p_pid)  # process owning the given hwnd
    hProcHnd = OpenProcess(win32con.PROCESS_ALL_ACCESS, False, struct.unpack("i", pid)[0])
    pLVI = VirtualAllocEx(hProcHnd, 0, 4096, win32con.MEM_RESERVE | win32con.MEM_COMMIT, win32con.PAGE_READWRITE)
    pBuffer = VirtualAllocEx(hProcHnd, 0, 4096, win32con.MEM_RESERVE | win32con.MEM_COMMIT, win32con.PAGE_READWRITE)

    # Prepare an LVITEM record and write it to target process memory
    lvitem_str = struct.pack('iiiiiiiii', *[0, 0, column_index, 0, 0, pBuffer, 4096, 0, 0])
    lvitem_buffer = ctypes.create_string_buffer(lvitem_str)
    copied = ctypes.create_string_buffer(4)
    p_copied = ctypes.addressof(copied)
    WriteProcessMemory(hProcHnd, pLVI, ctypes.addressof(lvitem_buffer), ctypes.sizeof(lvitem_buffer), p_copied)

    # iterate items in the SysListView32 control
    num_items = win32gui.SendMessage(hwnd, commctrl.LVM_GETITEMCOUNT)
    item_texts = []
    for item_index in range(num_items):
        win32gui.SendMessage(hwnd, commctrl.LVM_GETITEMTEXT, item_index, pLVI)
        target_buff = ctypes.create_string_buffer(4096)
        ReadProcessMemory(hProcHnd, pBuffer, ctypes.addressof(target_buff), 4096, p_copied)
        item_texts.append(target_buff.value)

    VirtualFreeEx(hProcHnd, pBuffer, 0, win32con.MEM_RELEASE)
    VirtualFreeEx(hProcHnd, pLVI, 0, win32con.MEM_RELEASE)
    win32api.CloseHandle(hProcHnd)
    return item_texts


def getListViewInfo(hwnd, cols):
    """
    ??????ListView?????????
    :param hwnd: sysListView??????
    :param cols: ???????????????
    :return: sysListView????????????
    """
    col_info = []
    for col in range(cols):
        col_info.append(_readListViewItems(hwnd, col))
    row_info = []

    # ??????
    for row in range(len(col_info[0])):
        row_info.append([])
        for col in range(len(col_info)):
            row_info[row].append(col_info[col][row].decode('GB2312'))
    return row_info


def findTopWindow(wantedText=None, wantedClass=None):
    """
    :param wantedText: ????????????
    :param wantedClass: ????????????
    :return: ???????????????????????????
    """
    return win32gui.FindWindow(wantedClass, wantedText)


def findPopupWindow(hwnd):
    """
    :param hwnd: ???????????????
    :return: ??????????????????????????????
    """
    return win32gui.GetWindow(hwnd, win32con.GW_ENABLEDPOPUP)


def dumpWindow(hwnd, wantedText=None, wantedClass=None):
    """
    :param hwnd: ????????????
    :param wantedText: ??????????????????
    :param wantedClass: ?????????????????????
    :return: ??????????????????????????????????????????
    """
    windows = []
    hwndChild = None
    while True:
        hwndChild = win32gui.FindWindowEx(hwnd, hwndChild, wantedClass, wantedText)
        if hwndChild:
            textName = win32gui.GetWindowText(hwndChild)
            className = win32gui.GetClassName(hwndChild)
            windows.append((hwndChild, textName, className))
        else:
            return windows


def findSubWindows(windows, numChildWindows):
    """
    ?????????????????????????????????????????????????????????????????????
    :param windows: ????????????
    :param numChildWindows: ???????????????
    :return:?????????????????????????????????hwnd, title, className
    """
    for window in windows:
        childHwnd, windowText, windowClass = window
        windowContent = dumpWindow(childHwnd)
        if len(windowContent) == numChildWindows:
            return windowContent


def findSubWindow(windows, wantedText=None, wantedClass=None):
    """
    ??????????????????????????????wantedText???wantedClass
    :param windows: ????????????
    :param wantedText: ????????????
    :param wantedClass: ????????????
    :return:????????????
    """
    for window in windows:
        childHwnd, windowText, windowClass = window
        if windowText == wantedText and windowClass == wantedClass:
            return childHwnd


def dumpWindows(hwnd):
    """Dump all controls from a window

    Useful during development, allowing to you discover the structure of the
    contents of a window, showing the text and class of all contained controls.

    Parameters
    ----------
    hwnd
        The window handle of the top level window to dump.

    Returns
    -------
        all windows

    Usage example::

        replaceDialog = findTopWindow(wantedText='Replace')
        pprint.pprint(dumpWindow(replaceDialog))
    """
    windows = []
    win32gui.EnumChildWindows(hwnd, _windowEnumerationHandler, windows)
    return windows


def closePopupWindows(top_hwnd):
    """
    ?????????????????????????????????????????????????????????
    :param top_hwnd: ???????????????
    :return:
    """
    while _closePopupWindow(top_hwnd):
        time.sleep(0.3)


def findControl(topHwnd,
                wantedText=None,
                wantedClass=None,
                selectionFunction=None):
    """Find a control.

    You can identify a control using caption, class, a custom selection
    function, or any combination of these. (Multiple selection criteria are
    ANDed. If this isn't what's wanted, use a selection function.)

    Parameters
    ----------
    topHwnd
        The window handle of the top level window in which the
        required controls reside.
    wantedText
        Text which the required control's captions must contain.
    wantedClass
        Class to which the required control must belong.
    selectionFunction
        Control selection function. Reference to a function
        should be passed here. The function should take hwnd as
        an argument, and should return True when passed the
        hwnd of the desired control.

    Returns
    -------
    The window handle of the first control matching the
    supplied selection criteria.

    Raises
    ------
    WinGuiAutoError, when no control found.

    Usage example::

        optDialog = findTopWindow(wantedText="Options")
        okButton = findControl(optDialog,
                               wantedClass="Button",
                               wantedText="OK")
    """
    controls = findControls(topHwnd,
                            wantedText=wantedText,
                            wantedClass=wantedClass,
                            selectionFunction=selectionFunction)
    if controls:
        return controls[0]
    else:
        raise WinGuiAutoError("No control found for topHwnd=" +
                              repr(topHwnd) +
                              ", wantedText=" +
                              repr(wantedText) +
                              ", wantedClass=" +
                              repr(wantedClass) +
                              ", selectionFunction=" +
                              repr(selectionFunction))


def findControls(topHwnd,
                 wantedText=None,
                 wantedClass=None,
                 selectionFunction=None):
    """Find controls.

    You can identify controls using captions, classes, a custom selection
    function, or any combination of these. (Multiple selection criteria are
    ANDed. If this isn't what's wanted, use a selection function.)

    Parameters
    ----------
    topHwnd
        The window handle of the top level window in which the
        required controls reside.
    wantedText
        Text which the required controls' captions must contain.
    wantedClass
        Class to which the required controls must belong.
    selectionFunction
        Control selection function. Reference to a function
        should be passed here. The function should take hwnd as
        an argument, and should return True when passed the
        hwnd of a desired control.

    Returns
    -------
    The window handles of the controls matching the
    supplied selection criteria.

    Usage example::

        optDialog = findTopWindow(wantedText="Options")
        def findButtons(hwnd, windowText, windowClass):
            return windowClass == "Button"
        buttons = findControl(optDialog, wantedText="Button")
    """

    def searchChildWindows(currentHwnd):
        results = []
        childWindows = []
        try:
            win32gui.EnumChildWindows(currentHwnd,
                                      _windowEnumerationHandler,
                                      childWindows)
        except win32gui.error:
            # This seems to mean that the control *cannot* have child windows,
            # i.e. not a container.
            return
        for childHwnd, windowText, windowClass in childWindows:
            descendentMatchingHwnds = searchChildWindows(childHwnd)
            if descendentMatchingHwnds:
                results += descendentMatchingHwnds

            if wantedText and \
                    not _normaliseText(wantedText) in _normaliseText(windowText):
                continue
            if wantedClass and \
                    not windowClass == wantedClass:
                continue
            if selectionFunction and \
                    not selectionFunction(childHwnd):
                continue
            results.append(childHwnd)
        return results

    return searchChildWindows(topHwnd)


def clickButton(hwnd):
    """Simulates a single mouse click on a button

    Parameters
    ----------
    hwnd
        Window handle of the required button.

    Usage example::

        okButton = findControl(fontDialog,
                               wantedClass="Button",
                               wantedText="OK")
        clickButton(okButton)
    """
    _sendNotifyMessage(hwnd, win32con.BN_CLICKED)


def click(hwnd):
    """
    ????????????????????????
    :param hwnd: ?????????????????????????????????
    :return:
    """
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONDOWN, None, None)
    time.sleep(.2)
    win32gui.PostMessage(hwnd, win32con.WM_LBUTTONUP, None, None)


def focusWindow(hwnd):
    """
    ??????????????????
    :param hwnd: ????????????
    :return:
    """
    win32gui.ShowWindow(hwnd, win32con.SW_SHOWMAXIMIZED)
    win32gui.SetForegroundWindow(hwnd)


def clickMenuButton(hwnd, offset):
    left, top, right, bottom = win32gui.GetWindowRect(hwnd)
    win32api.SetCursorPos([left + offset, (bottom - top) // 2 + top])
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.1)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
    time.sleep(0.3)


def sendKey(hwnd, key_code):
    """
    ????????????
    :param hwnd: ????????????
    :param key_code: ???????????????win32con????????????win32con.VK_F1
    :return:
    """
    win32gui.PostMessage(hwnd, win32con.WM_KEYDOWN, key_code, 0)  # ????????????
    time.sleep(.2)
    win32gui.PostMessage(hwnd, win32con.WM_KEYUP, key_code, 0)


def clickStatic(hwnd):
    """Simulates a single mouse click on a static

    Parameters
    ----------
    hwnd
        Window handle of the required static.

    Usage example:  TODO
    """
    _sendNotifyMessage(hwnd, win32con.STN_CLICKED)


def doubleClickStatic(hwnd):
    """Simulates a double mouse click on a static

    Parameters
    ----------
    hwnd
        Window handle of the required static.

    Usage example:  TODO
    """
    _sendNotifyMessage(hwnd, win32con.STN_DBLCLK)


# def getEditText(hwnd):
#     bufLen = win32gui.SendMessage(hwnd, win32con.WM_GETTEXTLENGTH, 0, 0) + 1
#     print(bufLen)
#     buffer = win32gui.PyMakeBuffer(bufLen)
#     win32gui.SendMessage(hwnd, win32con.WM_GETTEXT, bufLen, buffer)
#
#     text = buffer[:bufLen]
#     return text


def getWindowText(hwnd):
    return win32gui.GetWindowText(hwnd)


def setEditText(hwnd, text):
    """
    ??????Edit?????????????????????????????????????????????
    :param hwnd: Edit????????????
    :param text: ??????????????????
    :return:
    """
    win32gui.SendMessage(hwnd, win32con.WM_SETTEXT, None, text)


# def setEditText(hwnd, text, append=False):
#     '''Set an edit control's text.
#
#     Parameters
#     ----------
#     hwnd
#         The edit control's hwnd.
#     text
#         The text to send to the control. This can be a single
#         string, or a sequence of strings. If the latter, each will
#         be become a a seperate line in the control.
#     append
#         Should the new text be appended to the existing text?
#         Defaults to False, meaning that any existing text will be
#         replaced. If True, the new text will be appended to the end
#         of the existing text.
#         Note that the first line of the new text will be directly
#         appended to the end of the last line of the existing text.
#         If appending lines of text, you may wish to pass in an
#         empty string as the 1st element of the 'text' argument.
#
#     Usage example::
#
#         print "Enter various bits of text."
#         setEditText(editArea, "Hello, again!")
#         time.sleep(.5)
#         setEditText(editArea, "You still there?")
#         time.sleep(.5)
#         setEditText(editArea, ["Here come", "two lines!"])
#         time.sleep(.5)
#
#         print "Add some..."
#         setEditText(editArea, ["", "And a 3rd one!"], append=True)
#         time.sleep(.5)
#     '''

# Ensure that text is a list
# try:
#     text + ''
#     text = [text]
# except TypeError:
#     pass
#
# # Set the current selection range, depending on append flag
# if append:
#     win32gui.SendMessage(hwnd,
#                          win32con.EM_SETSEL,
#                          -1,
#                          0)
# else:
#     win32gui.SendMessage(hwnd,
#                          win32con.EM_SETSEL,
#                          0,
#                          -1)
#
# # Send the text
# win32gui.SendMessage(hwnd,
#                      win32con.EM_REPLACESEL,
#                      True,
#                      os.linesep.join(text))


def _closePopupWindow(top_hwnd, wantedText=None, wantedClass=None):
    """
    ?????????????????????
    :param top_hwnd: ???????????????
    :param wantedText: ?????????????????????????????????
    :param wantedClass: ?????????????????????????????????
    :return: ????????????????????????????????????True???????????????False
    """
    hwnd_popup = findPopupWindow(top_hwnd)
    if hwnd_popup:
        hwnd_control = findControl(hwnd_popup, wantedText, wantedClass)
        clickButton(hwnd_control)
        return True
    return False


def _windowEnumerationHandler(hwnd, resultList):
    """Pass to win32gui.EnumWindows() to generate list of window handle,
    window text, window class tuples."""
    resultList.append((hwnd,
                       win32gui.GetWindowText(hwnd),
                       win32gui.GetClassName(hwnd)))


def _buildWinLong(high, low):
    """Build a windows long parameter from high and low words.
    See http://support.microsoft.com/support/kb/articles/q189/1/70.asp
    """
    # return ((high << 16) | low)
    return int(struct.unpack('>L',
                             struct.pack('>2H',
                                         high,
                                         low))[0])


def _sendNotifyMessage(hwnd, nofifyMessage):
    """Send a notify message to a control."""
    win32gui.SendMessage(win32gui.GetParent(hwnd),
                         win32con.WM_COMMAND,
                         _buildWinLong(nofifyMessage,
                                       win32api.GetWindowLong(hwnd,
                                                              win32con.GWL_ID)),
                         hwnd)


def _normaliseText(controlText):
    """Remove '&' characters, and lower case.
    Useful for matching control text."""
    return controlText.lower().replace('&', '')


class Bunch(object):
    """See http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52308"""

    def __init__(self, **kwds):
        self.__dict__.update(kwds)

    def __str__(self):
        state = ["%s=%r" % (attribute, value)
                 for (attribute, value)
                 in list(self.__dict__.items())]
        return '\n'.join(state)


class WinGuiAutoError(Exception):
    pass
