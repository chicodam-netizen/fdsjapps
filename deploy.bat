@echo off
echo ========================================================
echo        SISTEMA QRZ - Sincronizacao e Deploy Automatico
echo ========================================================
echo.

:: Verifica se o Git esta instalado e acessivel
where git >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERRO] Git nao encontrado no seu sistema. Por favor, instale o Git.
    pause
    exit /b 1
)

echo [1/4] Verificando status dos arquivos em QRZ...
git status -s .
echo.

echo [2/4] Preparando para enviar alteracoes...
set /p commit_msg="Digite uma mensagem para o commit (pressione Enter para 'Update: auto-deploy'): "
if "%commit_msg%"=="" set commit_msg=Update: auto-deploy

echo.
echo [3/4] Adicionando arquivos e realizando commit...
git add .
git commit -m "%commit_msg%"
echo.
echo [4/4] Enviando alteracoes para o repositorio remoto (GitHub)...
git push fdsjapps main

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo  [SUCESSO] Codigo enviado ao GitHub com sucesso!
    echo  O Streamlit Cloud ira processar e atualizar o app em:
    echo  https://gestaoindustrialqrz.streamlit.app/
    echo ========================================================
) else (
    echo.
    echo [ERRO] Falha ao enviar para o GitHub. Verifique sua conexao e credenciais.
)

echo.
pause
