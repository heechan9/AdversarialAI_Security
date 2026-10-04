@echo off
call conda run --no-capture-output -n adversarial_ai python "%~dp0stage_b_original_environment.py" --execute --require-recorded-environment
if errorlevel 1 (
  echo Trace incomplete. Keep the printed return-evidence.zip and error message.
  exit /b 1
)
echo Send only the printed return-evidence.zip. This is not a Stage B approval.
