$env:MINIYT_SKIP_LAUNCH = '1'
$src = 'https://raw.githubusercontent.com/ieproject-app/mini-YT-Downloader/main/install.ps1'
$tmp = Join-Path $env:TEMP 'miniyt-install.ps1'
Invoke-WebRequest -Uri $src -OutFile $tmp -UseBasicParsing
& $tmp
