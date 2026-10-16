from PySide6.QtGui import QColor

TEXT = "#e6eefc"
TEXT_MUTED = "rgba(230, 238, 252, 150)"


def _c(hue: int, s: float, l: float) -> QColor:
    return QColor.fromHslF((hue % 360) / 360.0, s, l)


def background(hue: int) -> QColor:
    return _c(hue, 0.55, 0.10)


def chrome(hue: int) -> QColor:
    return _c(hue, 0.55, 0.065)


def accent(hue: int) -> QColor:
    return _c(hue, 0.85, 0.62)


def toolbutton_stylesheet() -> str:
    return f"""
        QToolButton {{
            background: transparent;
            border: none;
            border-radius: 4px;
            color: {TEXT};
            font-family: "Segoe MDL2 Assets";
            font-size: 10pt;
        }}
        QToolButton:hover {{
            background: rgba(255, 255, 255, 0.12);
        }}
        QToolButton:pressed {{
            background: rgba(255, 255, 255, 0.20);
        }}
        QToolButton#close:hover, QToolButton#ItemBtnClose:hover {{
            background: rgba(255, 255, 255, 0.12);
            color: #e81123;
        }}
        QToolButton#close:pressed, QToolButton#ItemBtnClose:pressed {{
            background: rgba(255, 255, 255, 0.20);
            color: #e81123;
        }}
    """


def scrollbar_stylesheet(hue: int) -> str:
    acc = accent(hue).name()
    return f"""
        /* Vertical Scrollbar */
        QScrollBar:vertical {{
            background: transparent;
            width: 8px;
            margin: 0px 0px 0px 0px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical {{
            background: rgba(255, 255, 255, 0.22);
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {acc};
        }}
        QScrollBar::handle:vertical:pressed {{
            background: {acc};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0px;
            background: none;
        }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            background: none;
        }}

        /* Horizontal Scrollbar */
        QScrollBar:horizontal {{
            background: transparent;
            height: 8px;
            margin: 0px 0px 0px 0px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: rgba(255, 255, 255, 0.22);
            min-width: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {acc};
        }}
        QScrollBar::handle:horizontal:pressed {{
            background: {acc};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0px;
            background: none;
        }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            background: none;
        }}
    """
