$ErrorActionPreference = "Continue"
Set-Location -LiteralPath $PSScriptRoot

try {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Docker Desktop no está iniciado. Ábrelo y vuelve a intentarlo." -ForegroundColor Red
        exit 1
    }

    Write-Host "Iniciando laboratorio OSCPT Enum Trainer..."
    Write-Host "Acceso DevPortal: http://localhost:8011/devportal/"
    Write-Host "Acceso Plataforma Retos: http://localhost:8011/help/"
    Write-Host "Para detenerlo y borrar sus recursos, pulsa Ctrl+C."
    docker compose up --build
}
finally {
    Write-Host ""
    Write-Host "Limpiando recursos del laboratorio..."
    docker compose down --rmi all --volumes --remove-orphans
    Write-Host "Laboratorio detenido. Contenedores, red e imagen del proyecto eliminados."
}
