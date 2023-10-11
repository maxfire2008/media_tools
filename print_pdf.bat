@echo off
if "%~1" == "" (
    echo Drag and drop a PDF onto this script to print it.
    pause
    exit
)

set PDFPath=%~1

:compress
py "C:\Users\Max\Documents\media_tools\print_pdf.py" "%PDFPath%"

pause
