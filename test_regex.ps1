$content = Get-Content 'D:\data\camfrog-autodj\config.example.toml' -Raw
Write-Host "Content length: $($content.Length)"

# Test bot_nick
if ($content -match 'bot_nick = "AutoDJ"') {
    Write-Host "bot_nick MATCH: $($matches[0])"
} else {
    Write-Host "bot_nick NO MATCH"
}

# Test admins
if ($content -match 'admins = \[".*"\]') {
    Write-Host "admins MATCH: $($matches[0])"
} else {
    Write-Host "admins NO MATCH"
}

# Test music_dirs
if ($content -match 'music_dirs = \[".*"\]') {
    Write-Host "music_dirs MATCH: $($matches[0])"
} else {
    Write-Host "music_dirs NO MATCH"
}

# Try the actual replacement
try {
    $newContent = $content -replace 'bot_nick = "AutoDJ"', 'bot_nick = "TestBot"'
    Write-Host "bot_nick replace: SUCCESS"
} catch {
    Write-Host "bot_nick replace FAILED: $_"
}

try {
    $newContent = $content -replace 'admins = \["Seaza"\]', 'admins = ["TestAdmin"]'
    Write-Host "admins replace: SUCCESS"
} catch {
    Write-Host "admins replace FAILED: $_"
}

try {
    $newContent = $content -replace 'music_dirs = \["D:/Music"\]', 'music_dirs = ["D:/NewMusic"]'
    Write-Host "music_dirs replace: SUCCESS"
} catch {
    Write-Host "music_dirs replace FAILED: $_"
}