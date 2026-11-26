@echo off
title MecaniQA - Teste de Estresse e Escalonamento HPA ao Vivo
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0executar-ao-vivo.ps1"
pause
