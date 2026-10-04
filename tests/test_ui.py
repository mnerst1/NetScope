import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QApplication
from netscope.repositories.database import Repository
from netscope.ui.window import Window
from netscope.i18n import LOCALES


def test_all_pages_languages_themes(tmp_path):
    app=QApplication.instance() or QApplication([])
    repo=Repository(tmp_path/'demo.db')
    window=Window(repo,demo=True,smoke=True)
    window.show()
    app.processEvents()
    assert window.devices_table.rowCount()==7
    for locale in LOCALES:
        window.change_language(locale)
        app.processEvents()
        assert window.stack.count()==9
        for page in range(9):
            window.navigate(page)
            app.processEvents()
    for theme in ('light','dark','system'):
        for style in ('fluent','glass','graphite','minimal','compact','oled'):
            repo.set_setting('style',style)
            window.change_appearance('theme',theme)
            app.processEvents()
    window.run_diagnostics()
    window.pool.waitForDone(5000)
    app.processEvents()
    assert window.diagnostic_table.rowCount()==3
    window.save_snapshot()
    window.compare()
    window.quit()
    app.processEvents()
