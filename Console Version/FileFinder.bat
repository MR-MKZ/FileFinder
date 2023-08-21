@echo off
title Install/Update requirements
python3.11\python.exe -m pip install -r requirements.txt --no-warn-script-location

title File Finder - Created By Mr.MKZ
cls
python3.11\python.exe main.py
pause