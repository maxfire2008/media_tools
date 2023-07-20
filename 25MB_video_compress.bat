@echo off
if "%~1" == "" (
    echo Drag and drop a video file onto this script to compress it.
    pause
    exit
)

set VideoPath=%~1
set TargetFileSizeMB=25

:compress
py "C:\Users\Max\Documents\scripts\compress_video.py" "%VideoPath%" %TargetFileSizeMB%

pause
