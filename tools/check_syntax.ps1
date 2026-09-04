Set-Location -Path 'D:\Users\Joshua\Desktop\proyectos'
& 'F:\Python311\python.exe' -m py_compile 'src\app.py'
if ($LASTEXITCODE -eq 0) { 'OK' } else { 'FAIL' }
