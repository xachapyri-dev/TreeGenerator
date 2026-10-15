import webbrowser
from PyQt6 import QtWidgets, QtCore
from UI.LanguageSelect import Ui_Dialog
from UI.Settings import Ui_Settings
from localization import LocalizationManager


class FirstRunLanguageDialog(QtWidgets.QDialog, Ui_Dialog):
    def __init__(self, loc_mgr: LocalizationManager, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.loc_mgr = loc_mgr

        self.langs = self.loc_mgr.get_available_languages()
        self.comboBox.clear()
        for code, name in self.langs.items():
            self.comboBox.addItem(name, code)

        self.pushButton.clicked.connect(self.accept)

    def get_selected_language(self) -> str:
        return self.comboBox.currentData() or "ru"


class SettingsWindow(QtWidgets.QMainWindow, Ui_Settings):
    settings_changed = QtCore.pyqtSignal()

    def __init__(self, settings: dict, loc_mgr: LocalizationManager, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.settings = settings
        self.loc_mgr = loc_mgr

        self.tabWidget.setCurrentIndex(0)

        self.langselect.blockSignals(True)
        self.langselect.clear()
        available = self.loc_mgr.get_available_languages()
        for code, name in available.items():
            self.langselect.addItem(name, code)

        cur_lang = self.settings.get("language", "ru")
        idx = self.langselect.findData(cur_lang)
        if idx >= 0:
            self.langselect.setCurrentIndex(idx)
        self.langselect.blockSignals(False)

        self.langselect.currentIndexChanged.connect(self._on_lang_changed)

        self.commandLinkButton.clicked.connect(
            lambda: webbrowser.open("https://github.com/xachapyri-dev/TreeGenerator")
        )
        self.commandLinkButton_2.clicked.connect(
            lambda: webbrowser.open("https://xachapyri-dev.itch.io/tree-generator")
        )
        self.commandLinkButton_3.clicked.connect(
            lambda: webbrowser.open("https://t.me/kroshidanielYouTube")
        )

        self.apply_localization()

    def apply_localization(self):
        t = self.loc_mgr.tr
        self.setWindowTitle(t("settings_window_title", "Настройки"))
        self.tabWidget.setTabText(0, t("settings_tab_lang", "Язык"))
        self.tabWidget.setTabText(1, t("settings_tab_about", "О программе"))

        self.label.setText(t("settings_lang_label", "Язык приложения"))
        self.label_2.setText(t("about_title", "Генератор деревьев"))
        self.label_3.setText(f"<html><head/><body><p>{t('about_desc')}</p></body></html>")

        self.commandLinkButton.setText(t("about_github", "GitHub проекта"))
        self.commandLinkButton_2.setText(t("about_itch", "Itch.io проекта"))
        self.commandLinkButton_3.setText(t("about_telegram", "Telegram канал"))

    def _on_lang_changed(self):
        lang_code = self.langselect.currentData()
        if lang_code:
            self.settings["language"] = lang_code
            self.loc_mgr.set_language(lang_code)
            self.apply_localization()
            self.settings_changed.emit()