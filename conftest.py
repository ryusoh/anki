import builtins
import sys
import types
from unittest.mock import MagicMock

aqt_mock = MagicMock()
aqt_mock.appVersion = '24.11.0'
sys.modules['aqt'] = aqt_mock

for _mod in [
    'addcards',
    'addons',
    'browser',
    'browser.previewer',
    'dialogs',
    'editor',
    'editcurrent',
    'forms',
    'forms.editcurrent',
    'gui_hooks',
    'import_export',
    'import_export.importing',
    'main',
    'sound',
    'taskman',
    'tts',
    'utils',
    'webview',
]:
    _m = MagicMock()
    sys.modules[f'aqt.{_mod}'] = _m
    _curr = aqt_mock
    _parts = _mod.split('.')
    for _p in _parts[:-1]:
        _curr = getattr(_curr, _p)
    setattr(_curr, _parts[-1], _m)

sys.modules['anki'] = MagicMock()
sys.modules['anki.cards'] = MagicMock()
sys.modules['anki.consts'] = MagicMock()
sys.modules['anki.decks'] = MagicMock()
sys.modules['anki.errors'] = MagicMock()


class NotFoundError(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


sys.modules['anki.errors'].NotFoundError = NotFoundError
sys.modules['anki'].errors.NotFoundError = NotFoundError
sys.modules['anki.exporting'] = MagicMock()
sys.modules['anki.hooks'] = MagicMock()
sys.modules['anki.importing'] = MagicMock()
sys.modules['anki.media'] = MagicMock()
sys.modules['anki.models'] = MagicMock()
sys.modules['anki.notes'] = MagicMock()
sys.modules['anki.scheduler'] = MagicMock()
sys.modules['anki.scheduler.base'] = MagicMock()
sys.modules['anki.sound'] = MagicMock()
sys.modules['anki.storage'] = MagicMock()
sys.modules['anki.sync'] = MagicMock()
sys.modules['anki.utils'] = MagicMock()


def ids2str_fn(ids):
    return f"({','.join(str(x) for x in ids)})" if ids else "()"


def int_time_fn():
    return 1234567890


def field_checksum_fn(val):
    return 12345


sys.modules['anki.utils'].ids2str = ids2str_fn
sys.modules['anki'].utils.ids2str = ids2str_fn
sys.modules['anki.utils'].int_time = int_time_fn
sys.modules['anki'].utils.int_time = int_time_fn
sys.modules['anki.utils'].field_checksum = field_checksum_fn
sys.modules['anki'].utils.field_checksum = field_checksum_fn


class _FakeMultiCardPreviewer:
    class Adapter:
        pass


sys.modules['aqt.browser.previewer'].MultiCardPreviewer = _FakeMultiCardPreviewer
sys.modules['aqt'].browser.previewer.MultiCardPreviewer = _FakeMultiCardPreviewer


class _FakeQtModule(types.ModuleType):
    """Qt stub module: real base classes where needed, MagicMock otherwise."""

    def __getattr__(self, name):
        mock = MagicMock()
        setattr(self, name, mock)
        return mock


_aqt_qt = _FakeQtModule('aqt.qt')
sys.modules['aqt.qt'] = _aqt_qt
sys.modules['aqt'].qt = _aqt_qt


class _FakeQtBase:
    """Base for stub Qt classes used in class definitions only."""

    def __init__(self, *args, **kwargs):
        pass

    def __getattr__(self, name):
        return MagicMock()


sys.modules['aqt.editcurrent'].EditCurrent = type('EditCurrent', (_FakeQtBase,), {})
sys.modules['aqt'].editcurrent.EditCurrent = type('EditCurrent', (_FakeQtBase,), {})


_QT_SUBCLASSABLE = [
    'QAbstractListModel',
    'QAction',
    'QCheckBox',
    'QDialog',
    'QHBoxLayout',
    'QItemDelegate',
    'QLabel',
    'QListView',
    'QMenu',
    'QObject',
    'QPushButton',
    'QThread',
    'QValidator',
    'QVBoxLayout',
    'QWidget',
]
for _qt_name in _QT_SUBCLASSABLE:
    setattr(_aqt_qt, _qt_name, type(_qt_name, (_FakeQtBase,), {}))

# Explicit __all__ keeps `from aqt.qt import *` from tripping over the
# dynamic __getattr__ and gives wildcard-importing add-ons the names they
# reference (e.g. QMenu, QCursor in enhance_main_window).
_aqt_qt.__all__ = _QT_SUBCLASSABLE + [
    'Qt',
    'QAbstractAnimation',
    'QAbstractButton',
    'QAbstractItemView',
    'QAbstractPrintDialog',
    'QApplication',
    'QBoxLayout',
    'QBrush',
    'QBuffer',
    'QButtonGroup',
    'QByteArray',
    'QCalendarWidget',
    'QClipboard',
    'QCloseEvent',
    'QColor',
    'QColorButton',
    'QColorDialog',
    'QComboBox',
    'QCompleter',
    'QCursor',
    'QDataStream',
    'QDataWidgetMapper',
    'QDate',
    'QDateEdit',
    'QDateTime',
    'QDateTimeEdit',
    'QDial',
    'QDialogButtonBox',
    'QDir',
    'QDockWidget',
    'QDoubleSpinBox',
    'QDrag',
    'QElapsedTimer',
    'QEvent',
    'QFileDialog',
    'QFocusEvent',
    'QFont',
    'QFontComboBox',
    'QFontDialog',
    'QFormLayout',
    'QGestureEvent',
    'QGestureRecognizer',
    'QGraphicsBlurEffect',
    'QGraphicsColorizeEffect',
    'QGraphicsDropShadowEffect',
    'QGraphicsEffect',
    'QGraphicsEllipseItem',
    'QGraphicsItem',
    'QGraphicsLineItem',
    'QGraphicsOpacityEffect',
    'QGraphicsPaintDevice',
    'QGraphicsPixmapItem',
    'QGraphicsRectItem',
    'QGraphicsScene',
    'QGraphicsTextItem',
    'QGraphicsView',
    'QGridLayout',
    'QGroupBox',
    'QHeaderView',
    'QHelpEvent',
    'QHideEvent',
    'QIcon',
    'QImage',
    'QInputDialog',
    'QIntValidator',
    'QItemDelegate',
    'QItemSelectionModel',
    'QKeyEvent',
    'QKeyGrabButton',
    'QKeySequence',
    'QKeySequenceEdit',
    'QLCDNumber',
    'QLayout',
    'QLine',
    'QLineEdit',
    'QLineF',
    'QListWidget',
    'QListWidgetItem',
    'QMainWindow',
    'QMatrix',
    'QMenuBar',
    'QMessageBox',
    'QMimeData',
    'QMouseEvent',
    'QMovie',
    'QOffscreenSurface',
    'QOpenGLContext',
    'QOpenGLFramebufferObject',
    'QOpenGLPaintDevice',
    'QOpenGLWidget',
    'QOpenGLWindow',
    'QPageSetupDialog',
    'QPaintEvent',
    'QPainter',
    'QPalette',
    'QPanGesture',
    'QParallelAnimationGroup',
    'QPen',
    'QPinchGesture',
    'QPlainTextEdit',
    'QPoint',
    'QPointF',
    'QPolygon',
    'QPolygonF',
    'QPrintDialog',
    'QProgressBar',
    'QProgressDialog',
    'QPropertyAnimation',
    'QRadioButton',
    'QRect',
    'QRectF',
    'QRegExpValidator',
    'QRegularExpressionValidator',
    'QResizeEvent',
    'QRubberBand',
    'QScreen',
    'QScrollArea',
    'QScrollBar',
    'QSequentialAnimationGroup',
    'QShortcut',
    'QShortcutEvent',
    'QShowEvent',
    'QSize',
    'QSizeF',
    'QSizePolicy',
    'QSlider',
    'QSpinBox',
    'QSplashScreen',
    'QSplitter',
    'QStackedWidget',
    'QStatusBar',
    'QStatusTipEvent',
    'QStringListModel',
    'QStyle',
    'QStyleFactory',
    'QStyleOption',
    'QStyleOptionViewItem',
    'QStyledItemDelegate',
    'QSurface',
    'QSurfaceFormat',
    'QSwipeGesture',
    'QSystemTrayIcon',
    'QTabWidget',
    'QTableWidget',
    'QTableWidgetItem',
    'QTapAndHoldGesture',
    'QTapGesture',
    'QTextBrowser',
    'QTextEdit',
    'QThreadPool',
    'QTime',
    'QTimeEdit',
    'QTimeLine',
    'QTimer',
    'QTimerEvent',
    'QToolBox',
    'QToolButton',
    'QToolTip',
    'QTouchEvent',
    'QTransform',
    'QTreeWidget',
    'QTreeWidgetItem',
    'QUndoView',
    'QUrl',
    'QUrlQuery',
    'QUuid',
    'QValidator',
    'QWheelEvent',
    'QWhatsThis',
    'QWidgetAction',
    'QWindow',
    'QWizard',
    'QWizardPage',
    'pyqtSignal',
    'pyqtSlot',
    'sip',
]


class _FakeAddonDownloader:
    pass


sys.modules['aqt'].addons.GetAddons = _FakeAddonDownloader
sys.modules['aqt'].tts.TTSProcessPlayer = type('TTSProcessPlayer', (_FakeQtBase,), {})


# Mocks for rewrite_text_of_study_cards
class MockDeckBrowser:
    _renderStats = MagicMock()


class MockOverview:
    pass


class MockDeckBrowserModule:
    DeckBrowser = MockDeckBrowser


class MockOverviewModule:
    Overview = MockOverview


sys.modules['aqt.deckbrowser'] = MockDeckBrowserModule()
sys.modules['aqt.overview'] = MockOverviewModule()
builtins.DeckBrowser = MockDeckBrowser


# Stub PyQt so that add-on code that imports PyQt5/PyQt6 directly
# can class-define without requiring the native bindings.
sys.modules['PyQt5'] = MagicMock()
sys.modules['PyQt5.QtWidgets'] = MagicMock()
sys.modules['PyQt6'] = MagicMock()
sys.modules['PyQt6.QtWidgets'] = MagicMock()


# Mock for fa2_modified in graph analysis
sys.modules['fa2_modified'] = MagicMock()
