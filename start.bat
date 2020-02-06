@echo off
openfiles >NUL 2>&1 
if NOT %ERRORLEVEL% EQU 0 goto NotAdmin 
cd /d "%~dp0" && START code\gui\dist\gui.exe
goto End
:NotAdmin 
echo In order for Qwik Forecast to work you will need run the start.bat file as an administrator!
pause 
:End

