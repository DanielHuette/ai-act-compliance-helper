<#
.SYNOPSIS
  Builds and starts the AI Act Compliance Helper on Windows.
  Baut und startet den Konformitätshelfer unter Windows.

.DESCRIPTION
  Checks first that Docker is installed and running and that the legal texts are built, then
  starts the services. For every gap the script says what to do, in German or English: the
  language comes from COMPLIANCE_HELPER_LANG, else from the Windows display language.

  Prüft erst, ob Docker da ist und läuft, ob die Rechtstexte gebaut sind, und startet dann den
  Verbund. Bei jedem Mangel sagt das Skript, was zu tun ist, auf Deutsch oder Englisch.

.PARAMETER Small
  Alias -Klein. Build without the large embedding model: fast, but the search then compares only
  words, not meaning. Fine for a test run.

.PARAMETER Refresh
  Alias -Neu. Rebuild without the build cache.

.PARAMETER Stop
  Alias -Stopp. Stop the services.

.EXAMPLE
  .\scripts\start.ps1
.EXAMPLE
  .\scripts\start.ps1 -Small
.EXAMPLE
  .\scripts\start.ps1 -Stop
#>
[CmdletBinding()]
param(
    [Alias('Klein')][switch]$Small,
    [Alias('Neu')][switch]$Refresh,
    [Alias('Stopp')][switch]$Stop
)

$ErrorActionPreference = 'Stop'

$RootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $RootDir

$RequestedLanguage = if ($env:COMPLIANCE_HELPER_LANG) { $env:COMPLIANCE_HELPER_LANG } else { (Get-Culture).TwoLetterISOLanguageName }
$UiLanguage = if ($RequestedLanguage.ToLower().StartsWith('en')) { 'en' } else { 'de' }
$env:COMPLIANCE_HELPER_LANG = $UiLanguage

function Get-Message {
    param([string]$German, [string]$English)
    if ($UiLanguage -eq 'en') { $English } else { $German }
}

$UseColor = (-not $env:NO_COLOR)

function Write-Info    { param([string]$Text) Write-Host $Text }
function Write-Success { param([string]$Text) if ($UseColor) { Write-Host "[ok] $Text" -ForegroundColor Green } else { Write-Host "[ok] $Text" } }
function Write-Caution { param([string]$Text) if ($UseColor) { Write-Host "[!]  $Text" -ForegroundColor Yellow } else { Write-Host "[!]  $Text" } }
function Exit-WithError {
    param([string]$Text)
    if ($UseColor) { Write-Host "[x]  $Text" -ForegroundColor Red } else { Write-Host "[x]  $Text" }
    exit 1
}

$ProductName = Get-Message "Konformitaetshelfer" "AI Act Compliance Helper"
if ($UseColor) { Write-Host $ProductName -ForegroundColor White } else { Write-Info $ProductName }
Write-Info ""

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Exit-WithError (Get-Message `
        "Docker ist nicht installiert. Docker Desktop holen unter https://docs.docker.com/get-docker/" `
        "Docker is not installed. Get Docker Desktop at https://docs.docker.com/get-docker/")
}

# Only the exit code matters: "docker info" fails while the Docker daemon is down.
docker info 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Exit-WithError (Get-Message `
        "Docker ist installiert, laeuft aber nicht. Docker Desktop starten und warten, bis das Walsymbol ruhig steht." `
        "Docker is installed but not running. Start Docker Desktop and wait until the whale icon stops moving.")
}

$DockerVersion = (docker version --format '{{.Server.Version}}' 2>$null)
if (-not $DockerVersion) { $DockerVersion = Get-Message "Fassung unbekannt" "version unknown" }
Write-Success (Get-Message "Docker laeuft ($DockerVersion)" "Docker is running ($DockerVersion)")

docker compose version 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Exit-WithError (Get-Message `
        "docker compose fehlt. Es gehoert zu Docker Desktop dazu; sonst nachinstallieren: https://docs.docker.com/compose/install/" `
        "docker compose is missing. It comes with Docker Desktop; otherwise install it: https://docs.docker.com/compose/install/")
}

if ($Stop) {
    docker compose down
    Write-Success (Get-Message "Angehalten." "Stopped.")
    exit 0
}

$CorpusFile = Join-Path $RootDir 'data\processed\corpus.jsonl'
if (-not (Test-Path $CorpusFile)) {
    Exit-WithError (Get-Message `
        "Die Rechtstexte fehlen: data\processed\corpus.jsonl`n     Erst bauen:  compliance-helper build-corpus --language de" `
        "The legal texts are missing: data\processed\corpus.jsonl`n     Build them first:  compliance-helper build-corpus --language de")
}
$UnitCount = (Get-Content $CorpusFile -ReadCount 0).Count
Write-Success (Get-Message "Rechtstexte da: $UnitCount Rechtsstellen" "Legal texts present: $UnitCount legal units")

foreach ($IndexLang in @('de', 'en')) {
    $Infix = if ($IndexLang -eq 'de') { '' } else { ".$IndexLang" }
    if (Test-Path (Join-Path $RootDir "data\processed\search_index$Infix.meta.json.gz")) {
        Write-Success (Get-Message `
            "Suchbestand ($IndexLang) da - der Dienst muss beim Start nicht rechnen" `
            "Search index ($IndexLang) present - the service need not compute it at start")
    } else {
        Write-Caution (Get-Message `
            "Der Suchbestand ($IndexLang) fehlt. Der Dienst baut ihn beim Start selbst; ohne das grosse Modell bedeutet das schlechtere Fundstellen.`n     Besser vorher:  compliance-helper build-index --language $IndexLang" `
            "The search index ($IndexLang) is missing. The service builds it itself at start; without the large model that means poorer citations.`n     Better beforehand:  compliance-helper build-index --language $IndexLang")
    }
}

if (-not (Test-Path (Join-Path $RootDir '.env'))) {
    Write-Caution (Get-Message `
        "Keine .env vorhanden. Es gelten die Vorgaben.`n     Fuer ein Sprachmodell:  copy .env.example .env  und Schluessel eintragen." `
        "No .env present. The defaults apply.`n     For a language model:  copy .env.example .env  and enter the keys.")
}

if ($Small) {
    $env:WITH_SEARCH_MODEL = "0"
    if (-not $env:COMPLIANCE_HELPER_MEMORY) { $env:COMPLIANCE_HELPER_MEMORY = "1g" }
    Write-Caution (Get-Message `
        "Kleines Abbild: ohne das Modell bge-m3. Die Suche vergleicht dann nur Woerter, nicht Bedeutung." `
        "Small image: without the bge-m3 model. The search then compares only words, not meaning.")
} else {
    $env:WITH_SEARCH_MODEL = "1"
    Write-Info ""
    Write-Info (Get-Message `
        "Es wird gebaut. Beim ersten Mal dauert das lange: Einbettungsmodell und`nKreuzbewerter sind zusammen rund 7 Gigabyte gross und werden mit ins Abbild`ngelegt, damit der Container spaeter ohne Netz arbeiten kann." `
        "Building. The first time this takes long: the embedding model and the`ncross-encoder are about 7 gigabytes together and go into the image so that`nthe container can work offline later.")
}

Write-Info ""
$BuildArgs = @('compose', 'build')
if ($Refresh) { $BuildArgs += '--no-cache' }
& docker @BuildArgs
if ($LASTEXITCODE -ne 0) {
    Exit-WithError (Get-Message `
        "Der Bau ist fehlgeschlagen. Die letzte Meldung oben sagt, woran es lag. Haeufigste Ursachen: kein Netz beim Holen der Pakete, oder zu wenig Platz (fuer das grosse Abbild sind rund 12 Gigabyte frei noetig - nachsehen mit: docker system df)." `
        "The build failed. The last message above says why. Most common causes: no network while fetching the packages, or too little disk space (the large image needs about 12 gigabytes free - check with: docker system df).")
}
Write-Success (Get-Message "Abbild gebaut" "Image built")

$UpArgs = @('compose')
$UpArgs += @('up', '--detach')
& docker @UpArgs
if ($LASTEXITCODE -ne 0) {
    Exit-WithError (Get-Message `
        "Der Start ist fehlgeschlagen. Protokoll ansehen mit: docker compose logs app" `
        "The start failed. View the log with: docker compose logs app")
}

$Port = if ($env:COMPLIANCE_HELPER_PORT) { $env:COMPLIANCE_HELPER_PORT } else { "8000" }
$BaseUrl = "http://127.0.0.1:$Port"

Write-Info ""
Write-Host ((Get-Message "Der Dienst faehrt hoch" "The service is starting") + " ") -NoNewline
$Ready = $false
$Health = $null
for ($i = 0; $i -lt 90; $i++) {
    try {
        $Health = Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 2 -ErrorAction Stop
        $Ready = $true
        break
    } catch {
        Write-Host "." -NoNewline
        Start-Sleep -Seconds 2
    }
}
Write-Info ""

if (-not $Ready) {
    Write-Caution (Get-Message `
        "Der Dienst hat in drei Minuten nicht geantwortet. Das kann am grossen Modell liegen.`n     Protokoll ansehen mit:  docker compose logs --follow app" `
        "The service did not answer within three minutes. The large model may be the reason.`n     View the log with:  docker compose logs --follow app")
    exit 1
}

function Write-Field {
    param([string]$German, [string]$English, [string]$Value)
    Write-Info ("   " + (Get-Message $German $English).PadRight(19) + $Value)
}

Write-Info ""
Write-Success (Get-Message "Der Konformitaetshelfer laeuft." "The AI Act Compliance Helper is running.")
Write-Info ""
Write-Field "Oberflaeche:" "Interface:" "$BaseUrl/"
Write-Field "Zustandsbericht:" "Health report:" "$BaseUrl/health"
Write-Field "Schnittstelle:" "API:" "$BaseUrl/openapi.json"
Write-Info ""
Write-Field "Rechtsstellen:" "Legal units:" $Health.units
Write-Field "Suche mit:" "Search with:" $Health.embedding_model
Write-Field "Formulierung:" "Wording:" $Health.llm
foreach ($warning in $Health.warnings) { Write-Field "Hinweis:" "Note:" $warning }
Write-Info ""
Write-Info (Get-Message "Anhalten mit:  .\scripts\start.ps1 -Stopp" "Stop with:  .\scripts\start.ps1 -Stop")
