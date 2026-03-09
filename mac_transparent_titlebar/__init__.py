import sys
import ctypes
import ctypes.util
from aqt import mw, gui_hooks
from PyQt6.QtCore import Qt, QObject, QEvent
from PyQt6.QtWidgets import QApplication

# Keep a global reference to the filter so it doesn't get garbage collected
_drag_filter = None

class WindowDragFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            try:
                if event.button() == Qt.MouseButton.LeftButton:
                    global_pos = event.globalPosition().toPoint()
                    win_pos = mw.mapFromGlobal(global_pos)
                    
                    # Top 28px is typical titlebar height. 
                    # We start at x > 75 to avoid interfering with macOS traffic lights.
                    if 0 <= win_pos.y() <= 28 and win_pos.x() > 75:
                        if mw.windowHandle():
                            mw.windowHandle().startSystemMove()
            except Exception:
                pass
        return False

def make_window_transparent(win_id):
    if sys.platform != "darwin":
        return
        
    try:
        objc_lib = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))
        objc_lib.sel_registerName.restype = ctypes.c_void_p
        objc_lib.sel_registerName.argtypes = [ctypes.c_char_p]
        
        try:
            win_ptr = int(win_id)
        except TypeError:
            win_ptr = int(win_id.__int__())
            
        ns_view = ctypes.c_void_p(win_ptr)
        
        sel_window = objc_lib.sel_registerName(b"window")
        msgSend_ptr = ctypes.cast(objc_lib.objc_msgSend, ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p))
        ns_window = msgSend_ptr(ns_view, sel_window)
        
        if not ns_window:
            return
            
        # Make titlebar background transparent
        sel_setTitlebarAppearsTransparent = objc_lib.sel_registerName(b"setTitlebarAppearsTransparent:")
        msgSend_bool = ctypes.cast(objc_lib.objc_msgSend, ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool))
        msgSend_bool(ns_window, sel_setTitlebarAppearsTransparent, True)
        
        # Hide the text title
        sel_setTitleVisibility = objc_lib.sel_registerName(b"setTitleVisibility:")
        msgSend_int = ctypes.cast(objc_lib.objc_msgSend, ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int))
        msgSend_int(ns_window, sel_setTitleVisibility, 1)

        # Extend app content into the titlebar area
        sel_styleMask = objc_lib.sel_registerName(b"styleMask")
        msgSend_get_ulong = ctypes.cast(objc_lib.objc_msgSend, ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p))
        current_mask = msgSend_get_ulong(ns_window, sel_styleMask)
        
        new_mask = current_mask | (1 << 15) # NSWindowStyleMaskFullSizeContentView
        sel_setStyleMask = objc_lib.sel_registerName(b"setStyleMask:")
        msgSend_set_ulong = ctypes.cast(objc_lib.objc_msgSend, ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong))
        msgSend_set_ulong(ns_window, sel_setStyleMask, new_mask)

    except Exception as e:
        print(f"Error making titlebar transparent: {e}")

def on_main_window_did_init():
    global _drag_filter
    make_window_transparent(mw.winId())
    
    # Install the drag filter on the whole application
    if _drag_filter is None:
        _drag_filter = WindowDragFilter()
        QApplication.instance().installEventFilter(_drag_filter)

gui_hooks.main_window_did_init.append(on_main_window_did_init)

if mw:
    on_main_window_did_init()
