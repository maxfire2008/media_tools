@echo off
if "%~1" == "" (
    echo Drag and drop a video file onto this script to compress it.
    pause
    exit
)

set VideoPath=%~1
set TargetFileSizeMB=300K

:compress
py "C:\Users\Max\Documents\media_tools\compress_video.py" "%VideoPath%" %TargetFileSizeMB%

pause
