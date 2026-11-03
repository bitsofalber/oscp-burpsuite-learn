$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $PSScriptRoot

try {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker Desktop no está iniciado. Ábrelo y vuelve a intentarlo." -ForegroundColor Red
        exit 1
    }

    Write-Host "Iniciando laboratorio..."
    Write-Host "Acceso: http://localhost:8010/"
    Write-Host "Para detenerlo y borrar sus recursos, pulsa Ctrl+C."
    docker compose up --build
}
finally {
    Write-Host ""
    Write-Host "Limpiando recursos del laboratorio..."
    docker compose down --rmi all --volumes --remove-orphans
    Write-Host "Laboratorio detenido. Contenedores, red, volumen de datos e imagen del proyecto eliminados."
}
