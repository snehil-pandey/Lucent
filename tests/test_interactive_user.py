import os
import sys
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QApplication, QDialog, QVBoxLayout, QLabel, 
                               QPushButton, QHBoxLayout, QMessageBox)
from lucent.config import Look
from lucent.overlay import OverlayWindow
from lucent import winapi


class UserVerificationDialog(QDialog):
    def __init__(self, step_title, step_instruction, parent=None):
        super().__init__(parent, Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Lucent Interactive Verification")
        self.setMinimumWidth(420)
        lay = QVBoxLayout(self)

        title = QLabel(f"<b>Step: {step_title}</b>")
        title.setStyleSheet("font-size: 13pt; color: #38bdf8;")
        lay.addWidget(title)

        desc = QLabel(step_instruction)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 10.5pt; margin-top: 6px; margin-bottom: 12px;")
        lay.addWidget(desc)

        btn_box = QHBoxLayout()
        self.btn_pass = QPushButton("✓ PASS (Confirmed)")
        self.btn_pass.setStyleSheet("background: #15803d; color: white; padding: 8px 16px; font-weight: bold;")
        self.btn_fail = QPushButton("✕ FAIL (Issue Observed)")
        self.btn_fail.setStyleSheet("background: #b91c1c; color: white; padding: 8px 16px; font-weight: bold;")

        self.btn_pass.clicked.connect(self.accept)
        self.btn_fail.clicked.connect(self.reject)
        btn_box.addWidget(self.btn_pass)
        btn_box.addWidget(self.btn_fail)
        lay.addLayout(btn_box)


def run_interactive_suite():
    app = QApplication.instance() or QApplication(sys.argv)
    look = Look(opacity=0.85, hue=210, on_top=True)
    overlay = OverlayWindow(look)
    overlay.show()

    results = []

    def prompt(title, instruction):
        dialog = UserVerificationDialog(title, instruction, overlay)
        passed = (dialog.exec() == QDialog.Accepted)
        results.append((title, passed))
        return passed

    # Step 1: Visual appearance & transparency
    prompt(
        "1. Visual Appearance & Translucency",
        "Verify that the Lucent window is visible on your screen, floating on top, and partially translucent with a sleek glowing border."
    )

    # Step 2: Alt + Left Click Dragging
    prompt(
        "2. Alt + Left-Click Drag (Reposition Anywhere)",
        "Hold the 'Alt' key on your keyboard and Left-Click + Drag from anywhere inside the Lucent window.\n\n"
        "Verify that the entire window moves smoothly under your cursor without needing to grab the titlebar."
    )

    # Step 3: Quick Snapping (Alt+1 to Alt+5)
    overlay.snap_to("top-right")
    prompt(
        "3. Quick Snap Layout (Alt + 4 -> Top-Right)",
        "The window has automatically snapped to the Top-Right corner.\n\n"
        "Try pressing Alt+1 (Bottom-Left), Alt+2 (Bottom-Right), or Alt+5 (Center). Confirm the window snaps reliably."
    )

    # Step 4: Window Collapse
    overlay.toggle_collapse()
    prompt(
        "4. Window Collapse / Shading (Ctrl+K)",
        "The window should now be collapsed into ONLY its 36px titlebar strip.\n\n"
        "Verify that the body vanished and the window shaded upwards."
    )
    overlay.toggle_collapse()

    # Step 5: Invert / Dark Mode Filter
    overlay.set_invert_colors(True)
    prompt(
        "5. Invert / High Contrast Mode (Ctrl+I)",
        "Invert mode is now turned ON. The titlebar '◐' button should highlight blue.\n\n"
        "Verify that the visual invert indicator is active and readable."
    )
    overlay.set_invert_colors(False)

    # Step 6: Click-through mode test
    overlay.set_click_through(True)
    prompt(
        "6. Click-Through (Ghost Mode) Pass-Through",
        "Click-Through mode is now ENABLED! Mouse clicks on the overlay body should pass straight through to whatever window is behind it.\n\n"
        "Press Ctrl+Alt+M on your keyboard anywhere in Windows to toggle it back, or confirm if clicks pass through."
    )
    overlay.set_click_through(False)

    # Step 7: Screen capture resistance
    if winapi.WIN:
        overlay.set_hide_from_capture(True)
        prompt(
            "7. Screen Capture Protection (WDA_EXCLUDEFROMCAPTURE)",
            "Screen protection is enabled.\n\n"
            "Take a quick Windows screenshot snippet (Win + Shift + S) over this window. Confirm it is invisible or transparent in the snippet."
        )

    overlay.close()

    # Print summary
    print("\n" + "=" * 50)
    print("      LUCENT INTERACTIVE VERIFICATION REPORT")
    print("=" * 50)
    all_passed = True
    for title, status in results:
        sym = "✓ PASS" if status else "✕ FAIL"
        if not status:
            all_passed = False
        print(f"[{sym}] {title}")
    print("=" * 50)
    if all_passed:
        print("ALL USER CONFIRMATION CHECKS PASSED SUCCESSFULLY!\n")
    else:
        print("SOME CHECKS WERE MARKED AS FAILED BY USER.\n")


if __name__ == "__main__":
    run_interactive_suite()
