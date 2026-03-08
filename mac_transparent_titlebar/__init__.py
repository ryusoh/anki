import sys
import ctypes
import ctypes.util
from aqt import mw, gui_hooks

def make_window_transparent(win_id):
    if sys.platform != "darwin":
        return
        
    try:
        # Load objc and AppKit
        objc_lib = ctypes.cdll.LoadLibrary(ctypes.util.find_library('objc'))
        
        # Setup objc functions
        objc_lib.sel_registerName.restype = ctypes.c_void_p
        objc_lib.sel_registerName.argtypes = [ctypes.c_char_p]
        
        # Parse winId into an integer pointer
        try:
            win_ptr = int(win_id)
        except TypeError:
            win_ptr = int(win_id.__int__())
            
        ns_view = ctypes.c_void_p(win_ptr)
        
        # [ns_view window]
        sel_window = objc_lib.sel_registerName(b"window")
        msgSend_ptr = ctypes.cast(objc_lib.objc_msgSend, ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p))
        ns_window = msgSend_ptr(ns_view, sel_window)
        
        if not ns_window:
            return
            
        # [ns_window setTitlebarAppearsTransparent:YES]
        sel_setTitlebarAppearsTransparent = objc_lib.sel_registerName(b"setTitlebarAppearsTransparent:")
        msgSend_bool = ctypes.cast(objc_lib.objc_msgSend, ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool))
        msgSend_bool(ns_window, sel_setTitlebarAppearsTransparent, True)
        
        # [ns_window setTitleVisibility:1] # NSWindowTitleHidden = 1
        sel_setTitleVisibility = objc_lib.sel_registerName(b"setTitleVisibility:")
        msgSend_int = ctypes.cast(objc_lib.objc_msgSend, ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int))
        msgSend_int(ns_window, sel_setTitleVisibility, 1)
        
        # [ns_window setStyleMask:[ns_window styleMask] | (1 << 15)] # NSWindowStyleMaskFullSizeContentView = 1 << 15
        sel_styleMask = objc_lib.sel_registerName(b"styleMask")
        # styleMask returns NSUInteger (c_ulong on 64-bit)
        msgSend_get_ulong = ctypes.cast(objc_lib.objc_msgSend, ctypes.CFUNCTYPE(ctypes.c_ulong, ctypes.c_void_p, ctypes.c_void_p))
        current_mask = msgSend_get_ulong(ns_window, sel_styleMask)
        
        new_mask = current_mask | (1 << 15)
        sel_setStyleMask = objc_lib.sel_registerName(b"setStyleMask:")
        msgSend_set_ulong = ctypes.cast(objc_lib.objc_msgSend, ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong))
        msgSend_set_ulong(ns_window, sel_setStyleMask, new_mask)

    except Exception as e:
        print(f"Error making titlebar transparent: {e}")

def on_main_window_did_init():
    make_window_transparent(mw.winId())

gui_hooks.main_window_did_init.append(on_main_window_did_init)

if mw:
    make_window_transparent(mw.winId())
