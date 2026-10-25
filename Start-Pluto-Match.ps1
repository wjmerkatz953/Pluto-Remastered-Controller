[CmdletBinding()]
param(
    [ValidateSet('Human','CoG','V2')][string]$P1 = 'Human',
    [ValidateSet('Human','CoG','V2')][string]$P2 = 'V2',
    [switch]$VerifyOnly,
    [switch]$Observer,
    [ValidateSet('Default','English')][string]$Language = 'Default',
    [switch]$List,
    [string]$StarCraftRoot
)

# Experimental manual LAN match selector. Original working launchers are never modified.
$ErrorActionPreference = 'Stop'
# Qt QProcess consumes UTF-8; Powershell 5.1 otherwise emits cp949 Korean warnings.
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$dev = $PSScriptRoot
$original = Join-Path (Split-Path -Parent $dev) 'pluto-remastered-1v1-main'
$v2root = Join-Path (Split-Path -Parent $dev) 'pluto-v2.0'
. (Join-Path $original 'scripts\Common.ps1')

if ($List) {
    Write-Output 'Supported slots: Human | CoG | V2'
    Write-Output 'Examples:'
    Write-Output '  .\Start-Pluto-Match.cmd -P1 Human -P2 V2'
    Write-Output '  .\Start-Pluto-Match.cmd -P1 Human -P2 CoG'
    Write-Output '  .\Start-Pluto-Match.cmd -P1 CoG -P2 V2'
    Write-Output '  .\Start-Pluto-Match.cmd -P1 V2 -P2 V2'
    Write-Output '  Add -Observer for a third 64-bit spectator window (experimental).'
    Write-Output '  Add -Language English to request the enUS locale (experimental).'
    Write-Output '  Add -VerifyOnly to check files without launching the game.'
    Write-Output 'LAN lobby is MANUAL. P1 creates a PRIVATE LAN Melee room; P2 joins.'
    Write-Output 'V2 vs V2 and a third spectator were verified on one Windows PC; other machines untested.'
    return
}

$compat = Read-Json (Join-Path $original 'compatibility.json')
$gameRoot = Resolve-GameRoot $StarCraftRoot $original
Assert-SupportedGame $gameRoot $compat
Assert-LauncherFiles $original
Assert-FileHash (Join-Path $original 'maps\(4)Fighting_Spirit_1.3.scx') $compat.mapSha256
# Assert-LauncherFiles above already pins MultiInstance.exe (no duplicate verification).

$models = @{
    CoG = @{
        Model = Join-Path $original 'AI\pluto.dll'
        Infer = Join-Path $original 'AI\pluto\pluto_infer.exe'
        Weights = Join-Path $original 'AI\pluto\pluto_weights.bin'
        Bridge = Join-Path $original 'bin\pluto-scr.dll'
        Loader = Join-Path $original 'bin\scr-loader.exe'
        ModelHash = $compat.model.'pluto.dll'
        InferHash = $compat.model.'pluto/pluto_infer.exe'
        WeightsHash = $compat.model.'pluto/pluto_weights.bin'
        BridgeHash = $compat.bridge.'pluto-scr.dll'
        LoaderHash = $compat.bridge.'scr-loader.exe'
    }
    V2 = @{
        Model = Join-Path $v2root 'pluto.dll'
        Infer = Join-Path $v2root 'pluto\pluto_infer.exe'
        Weights = Join-Path $v2root 'pluto\pluto_weights.bin'
        Bridge = Join-Path $dev 'build-v2\Release\pluto-scr.dll'
        Loader = Join-Path $dev 'build-v2\Release\scr-loader.exe'
        ModelHash = '603fea2f77a4b652f29b832c2977cf5bc9d83bbcb927febd04499220020ce3bc'
        InferHash = '3f2814a51034b9817b396e52b38d30341ede506a2baedc7cbc11cb6ebcece2cc'
        WeightsHash = 'c53a559b4910777dc0e1c561c0d89d243091f465d8e9fc0f5f72e56597067d86'
        BridgeHash = 'd83b5707c85ee8155fd2faaf54e7932cc99349c97a2da5fe06ed297870e40e62'
        LoaderHash = '90c21c7b89049575bcdc01c4063bd1e610aa40f7048e272cadefd94ff812fc13'
    }
}

foreach($modelName in @($P1,$P2) | Where-Object { $_ -ne 'Human' } | Select-Object -Unique) {
    $entry=$models[$modelName]
    Assert-FileHash $entry.Model $entry.ModelHash
    Assert-FileHash $entry.Infer $entry.InferHash
    Assert-FileHash $entry.Weights $entry.WeightsHash
    Assert-FileHash $entry.Bridge $entry.BridgeHash
    Assert-FileHash $entry.Loader $entry.LoaderHash
}
Write-Output ("Models selected: P1={0}; P2={1}" -f $P1,$P2)
Write-Output ("Verified game: StarCraft Remastered {0}; Fighting Spirit 1.3" -f $compat.gameVersion)
Write-Output ("Options: Observer={0}; Language={1}" -f ([bool]$Observer),$Language)
$gameArgs=if($Language -eq 'English'){'-launch --locale=enUS'}else{'-launch'}
if ($VerifyOnly) {
    Write-Output 'PASS: exact SHA-256 of all selected game, models, bridges, and launchers.'
    Write-Output 'NOTE: no game processes started; verify match behavior separately on each PC.'
    return
}

if (Get-Process -Name StarCraft -ErrorAction SilentlyContinue) {
    throw 'StarCraft is already running. Close all existing StarCraft windows first. No process was terminated.'
}

$bonjour=Get-Service -Name 'Bonjour Service' -ErrorAction SilentlyContinue
if (!$bonjour -or $bonjour.Status -ne 'Running') {
    Start-Process -FilePath (Join-Path $gameRoot 'x86\ClientSdkMDNSHost.exe') -WindowStyle Hidden
    for ($i=0; $i -lt 60; $i++) {
        Start-Sleep -Milliseconds 500
        $bonjour=Get-Service -Name 'Bonjour Service' -ErrorAction SilentlyContinue
        if ($bonjour -and $bonjour.Status -eq 'Running') { break }
    }
    if (!$bonjour -or $bonjour.Status -ne 'Running') {
        throw 'Bonjour LAN service is not running; enable LAN discovery first.'
    }
}

$mapDir=Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'StarCraft\Maps\Pluto'
New-Item -ItemType Directory -Path $mapDir -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $original 'maps\(4)Fighting_Spirit_1.3.scx') -Destination $mapDir -Force
$releaseExe=Join-Path $original 'bin\MultiInstance.exe'

function Wait-GameWindow([Diagnostics.Process]$game) {
    for ($i=0;$i -lt 60;$i++){
        $game.Refresh()
        if ($game.HasExited) { throw ("StarCraft PID {0} exited during startup." -f $game.Id) }
        if ($game.MainWindowHandle -ne 0) { return }
        Start-Sleep -Milliseconds 500
    }
    throw ("StarCraft PID {0} did not create a window." -f $game.Id)
}
function Launch-Player([int]$number,[string]$name) {
    $dir=Join-Path $dev ("match-player{0}" -f $number)
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    $isHuman=($name -eq 'Human')
    if (!$isHuman) {
        $entry=$models[$name]
        $oldLogs=@('bridge.log','pluto.log','pluto_infer.log') | ForEach-Object {Join-Path $dir $_} | Where-Object {Test-Path -LiteralPath $_}
        if ($oldLogs) {
            $archive=Join-Path $dir ('logs\'+(Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
            New-Item -ItemType Directory -Path $archive -Force | Out-Null
            foreach ($old in $oldLogs) { Copy-Item -LiteralPath $old -Destination $archive }
        }
        if(Test-Path -LiteralPath (Join-Path $dir 'bridge.log')){
            Clear-Content -LiteralPath (Join-Path $dir 'bridge.log')
        }
        Copy-Item -LiteralPath $entry.Bridge -Destination (Join-Path $dir 'pluto-scr.dll') -Force
        @('[pluto]',('module='+$entry.Model),'speed_ms=-1','multiplayer=1','challenge=0') |
            Set-Content -LiteralPath (Join-Path $dir 'bridge.ini') -Encoding Unicode
    }
    $exe=Join-Path $gameRoot $(if ($isHuman) {'x86_64\StarCraft.exe'} else {'x86\StarCraft.exe'})
    $previousStraddle=$env:BWRL_STRADDLE
    $previousBudget=$env:BWRL_FRAME_BUDGET_MS
    try {
        if (!$isHuman) {
            $env:BWRL_STRADDLE='1'
            $env:BWRL_FRAME_BUDGET_MS='10'
        }
        $game=Start-Process -FilePath $exe -ArgumentList $gameArgs -WorkingDirectory $dir -PassThru
    } finally {
        $env:BWRL_STRADDLE=$previousStraddle
        $env:BWRL_FRAME_BUDGET_MS=$previousBudget
    }
    Wait-GameWindow $game
    if (!$isHuman) {
        & $entry.Loader $game.Id (Join-Path $dir 'pluto-scr.dll') | Out-Host
        if ($LASTEXITCODE -ne 0) {
            throw ("P{0} {1}: bridge loader failed (exit {2}); inspect {3}" -f $number,$name,$LASTEXITCODE,(Join-Path $dir 'bridge.log'))
        }
        $ready=$false
        for ($i=0;$i -lt 30;$i++){
            $log=Join-Path $dir 'bridge.log'
            if ((Test-Path -LiteralPath $log) -and (Select-String -LiteralPath $log -SimpleMatch '"result":"MH_OK"' -Quiet)) {
                $ready=$true;break
            }
            Start-Sleep -Milliseconds 200
        }
        if (!$ready) {
            throw ("P{0} {1}: bridge did not initialize; inspect {2}" -f $number,$name,(Join-Path $dir 'bridge.log'))
        }
    }
    Write-Host ("P{0}: {1} ready | PID {2} | {3}" -f $number,$name,$game.Id,$dir)
    return $game
}

try {
    $first=Launch-Player -number 1 -name $P1
    & $releaseExe $first.Id --release
    if ($LASTEXITCODE -ne 0) { throw 'Failed to prepare second StarCraft window.' }
    $second=Launch-Player -number 2 -name $P2
    $spectator=$null
    if($Observer) {
        & $releaseExe $second.Id --release | Out-Host
        if($LASTEXITCODE -ne 0) { throw 'Failed to prepare third Observer window.' }
        $spectator=Launch-Player -number 3 -name 'Human'
        Write-Warning 'Third window is only a client. Join the private LAN lobby and assign it to an OBSERVER slot, not a player slot.'
    }
    # MainWindowHandle at initial startup is NOT proof a third instance persists.
    # Check the requested game clients after the last client has finished starting.
    Start-Sleep -Milliseconds 1700
    $requiredGames = @($first, $second)
    if ($Observer) { $requiredGames += $spectator }
    for ($idx = 0; $idx -lt $requiredGames.Count; $idx++) {
        $check = $requiredGames[$idx]
        $check.Refresh()
        if ($check.HasExited -or $check.MainWindowHandle -eq 0) {
            throw ("P{0} game window has disappeared after launch (PID {1}); verify actual game clients before reporting success." -f ($idx+1), $check.Id)
        }
        Write-Output ("WINDOW P{0}: PID={1} present, hwnd={2}" -f ($idx+1), $check.Id, $check.MainWindowHandle)
    }
    @{ P1=$P1;P2=$P2;P1Pid=$first.Id;P2Pid=$second.Id;ObserverPid=$(if($spectator){$spectator.Id}else{$null});Started=(Get-Date).ToString('o') } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $dev 'session-match.json') -Encoding UTF8
    Write-Output ''
    Write-Output ("READY FOR MANUAL PRIVATE LAN: P1={0} (host), P2={1} (join)" -f $P1,$P2)
    Write-Output 'Select Fighting Spirit 1.3, Melee, two human PLAYER slots (not Computer).'
    Write-Output 'Start the match manually from the host; bots take control after match start.'
    Write-Output 'Check each match-player1 / match-player2 bridge.log separately.'
    if($Observer){
        Write-Output 'P3 = your 64-bit OBSERVER (no AI bridge). Join and select Observer before starting the match.'
        Write-Warning 'A real observer must NOT count as a third active player, or the AI refuses the match.'
    }
    if($Language -eq 'English') {
        Write-Output 'Requested English with --locale=enUS for each game process; confirm menu language in-game.'
        Write-Output 'The pinned CoG bridge and v2 bridge may still print some messages in Korean.'
    }
    Write-Output 'After testing, close all StarCraft windows manually (two, or three with -Observer).'
    if ($P1 -ne 'Human' -and $P2 -ne 'Human') {
        Write-Warning 'V2 vs V2 verified on one PC (two complete observer-view matches); other PCs unverified.'
        Write-Warning 'Multiple inference processes need sufficient CPU and memory resources.'
    }
} catch {
    Write-Warning 'Startup failed. Existing windows were NOT terminated; inspect the corresponding logs.'
    throw
}
