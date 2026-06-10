# watch_deploy.ps1
# Codificação UTF-8 para compatibilidade de caracteres no PowerShell
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "        QRZ Streamlit Auto-Watcher & Deployer" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "Monitorando arquivos em D:\FD_CONSULTORIA\DESENVOLVIMENTO\QRZ... (Ctrl+C para parar)" -ForegroundColor Yellow
Write-Host ""

# Determina a raiz do projeto (onde fica o .git)
# Como este script fica na subpasta QRZ, o diretório atual resolve para QRZ.
$projectRoot = Resolve-Path "."
Write-Host "Pasta monitorada: $projectRoot" -ForegroundColor Gray

# Dicionário de estados dos arquivos
$fileStates = @{}

# Função para listar os arquivos válidos a monitorar (ignora pastas indesejadas)
function Get-ProjectFiles {
    Get-ChildItem -Path $projectRoot -Recurse -File | Where-Object {
        $_.FullName -notmatch "\\\.git\\" -and
        $_.FullName -notmatch "\\node_modules\\" -and
        $_.FullName -notmatch "\\__pycache__\\" -and
        ($_.Extension -eq ".py" -or $_.Extension -eq ".toml" -or $_.Extension -eq ".txt" -or $_.Extension -eq ".css" -or $_.Extension -eq ".html")
    }
}

# Inicializa o estado com a data da última modificação
Get-ProjectFiles | ForEach-Object {
    $fileStates[$_.FullName] = $_.LastWriteTime
}

$cooldownSeconds = 3
$lastChangeTime = $null
$changedFiles = @()

while ($true) {
    Start-Sleep -Milliseconds 500
    
    $currentFiles = Get-ProjectFiles
    $hasChanges = $false
    
    foreach ($file in $currentFiles) {
        $path = $file.FullName
        $lastWrite = $file.LastWriteTime
        
        if (-not $fileStates.ContainsKey($path)) {
            # Novo arquivo detectado
            $fileStates[$path] = $lastWrite
            $changedFiles += $file.Name
            $hasChanges = $true
            Write-Host "[NOVO] $($file.Name) detectado!" -ForegroundColor Green
        }
        elseif ($fileStates[$path] -ne $lastWrite) {
            # Modificação detectada
            $fileStates[$path] = $lastWrite
            $changedFiles += $file.Name
            $hasChanges = $true
            Write-Host "[MODIFICADO] $($file.Name) alterado!" -ForegroundColor Yellow
        }
    }
    
    if ($hasChanges) {
        $lastChangeTime = Get-Date
    }
    
    # Se houve alteração recente e passamos pelo tempo de cooldown (estabilização)
    if ($lastChangeTime -ne $null -and ( (Get-Date) - $lastChangeTime ).TotalSeconds -ge $cooldownSeconds) {
        Write-Host ""
        Write-Host "--------------------------------------------------------" -ForegroundColor Cyan
        Write-Host "Mudanças estabilizadas. Iniciando deploy automático..." -ForegroundColor Cyan
        
        $filesStr = $changedFiles -join ", "
        $commitMsg = "Auto-deploy: alterado ($filesStr)"
        if ($commitMsg.Length -gt 70) {
            $commitMsg = "Auto-deploy: multiplas alteracoes"
        }
        
        Write-Host "1. Sincronizando arquivos locais..." -ForegroundColor Gray
        git add .
        
        Write-Host "2. Criando commit: '$commitMsg'..." -ForegroundColor Gray
        git commit -m $commitMsg
        
        Write-Host "3. Enviando ao GitHub (push fdsjapps main)..." -ForegroundColor Gray
        git push fdsjapps main
        
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[SUCESSO] Deploy enviado automaticamente!" -ForegroundColor Green
            Write-Host "Acompanhe a atualização em: https://gestaoindustrialqrz.streamlit.app/" -ForegroundColor Green
        } else {
            Write-Host "[ERRO] Erro ao enviar para o GitHub. Verifique credenciais e rede." -ForegroundColor Red
        }
        Write-Host "--------------------------------------------------------" -ForegroundColor Cyan
        Write-Host ""
        
        # Reseta os controles
        $lastChangeTime = $null
        $changedFiles = @()
    }
}
