@echo off
echo ===================================================
echo   Deploying The Code Factory (Combined Branch)
echo ===================================================
echo.
git push -u origin combined --force
echo.
echo ===================================================
echo   Push Complete! Check your GitHub Actions tab:
echo   https://github.com/alien1611/the-code-factory/actions
echo ===================================================
pause
