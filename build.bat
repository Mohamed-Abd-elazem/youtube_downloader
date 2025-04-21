@echo off
echo Cleaning previous builds...
rmdir /s /q build
rmdir /s /q dist

echo Building application...
pyinstaller --clean youtube_downloader.spec

echo Build complete!
pause