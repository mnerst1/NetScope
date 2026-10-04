# Сборка Windows EXE без Visual Studio

## Надёжный onedir

Сборка выполняется на Windows x64. Тестируемый стек: Python 3.12.14 x64, PySide6 6.9.3, psutil 7.1.0, PyInstaller 6.16.0. Python, зависимости и Inno Setup нужны только разработчику, не конечному пользователю EXE.

Из папки проекта:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\package_release.ps1
```

Можно запустить `build.bat`. Скрипт проверяет тесты, запускает PyInstaller и проверяет EXE в изолированном DEMO-режиме с автоматическим выходом. При ошибке завершает сборку. В Qt не нужна отдельная системная установка: библиотеки и плагины берутся из PySide6 wheels.

Результат:

```text
dist/NetScope/NetScope.exe
dist/NetScope/_internal/...
release/NetScope-v1.0.0-Windows-x64.zip
```

Весь каталог `NetScope` нужно распространять целиком. Включены `qwindows.dll`, Qt runtime, SQLite/psutil, иконки, 23 JSON-каталога и локальный справочник производителей. `NetScope.spec` намеренно исключает другие Qt bindings, Tk и WebEngine. UPX выключен.

Если окружение имеет другое имя, передайте `-Python 'C:\полный\путь\python.exe'`. Сборка не зависит от абсолютных путей компьютера автора.

## Дополнительный onefile

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\build.ps1 -OneFile
```

`dist\NetScope-OneFile.exe`. При запуске он распаковывает Qt во временную папку и обычно запускается медленнее. Onedir остаётся рекомендуемым вариантом. Один успешный smoke test не доказывает стабильность на всех антивирусах и компьютерах; не заменяйте основной архив onefile без собственного тестирования.

## Дополнительный установщик

Установите Inno Setup 6, откройте `installer.iss`, нажмите Compile после onedir-сборки. Или:

```powershell
& 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' .\installer.iss
```

Получится `release\NetScope-Setup-v1.0.0.exe`. Установка для текущего пользователя: Start Menu, опциональный Desktop shortcut, удаление через настройки Windows. Visual Studio не нужен. База сохраняется после удаления; автозапуск удаляется. Установщик NetScope-Setup-v1.0.0.exe собран Inno Setup 6.7.3.

## Что проверено и чего проверка не доказывает

Onedir реально собран на Windows и запущен с `--smoke-test`: код выхода 0, создан скриншот. Это проверяет загрузку Python/Qt, ресурсов, переводов, базы, страниц и DEMO. Тесты охватывают смену языка и темы, логику базы и безопасные сетевые ограничения.

Проверка интерфейсов реально нашла Wi-Fi и локальный шлюз через Windows IP Helper API. ICMP в изолированной среде выполнения возвращает системный сбой; полноценное обнаружение реальной сети здесь не подтверждено. Перед релизом необходимы проверки на вашем ПК и чистой Windows без Python по `TEST_CHECKLIST.md`. Подписание кода не настроено. Публикация в GitHub выполняется по запросу владельца репозитория.
