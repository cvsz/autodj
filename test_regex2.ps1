$content = Get-Content 'D:\data\camfrog-autodj\config.example.toml' -Raw
$botNick = "TestBot"
$adminNick = "TestAdmin"
$musicDir = "D:\Music"

Write-Host "Testing variable expansion in replacement..."

# Test the exact pattern from the script
try {
    $result = $content -replace 'bot_nick = "AutoDJ"', "bot_nick = `"$botNick`""
    Write-Host "bot_nick replace with var: SUCCESS"
    Write-Host "Result: $($result -match 'bot_nick = \"TestBot\"')"
} catch {
    Write-Host "bot_nick replace with var FAILED: $_"
    Write-Host "Error type: $($_.GetType().FullName)"
    Write-Host "Error position: $($_.InvocationInfo.PositionMessage)"
}

try {
    $result = $content -replace 'admins = \["Seaza"\]', "admins = `[`"$adminNick`"`]"
    Write-Host "admins replace with var: SUCCESS"
} catch {
    Write-Host "admins replace with var FAILED: $_"
}

try {
    $musicDirFixed = $musicDir -replace '\\', '/'
    $result = $content -replace 'music_dirs = \["D:/Music"\]', "music_dirs = `[`"$musicDirFixed`"`]"
    Write-Host "music_dirs replace with var: SUCCESS"
} catch {
    Write-Host "music_dirs replace with var FAILED: $_"
}