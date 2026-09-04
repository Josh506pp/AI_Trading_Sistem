Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Stop-Process -Name terminal64 -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
Set-Location -Path 'D:\Users\Joshua\Desktop\proyectos'
& 'F:\Python311\python.exe' 'src\app.py'
