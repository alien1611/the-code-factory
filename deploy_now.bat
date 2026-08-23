@echo off
echo =========================================================
echo   THE CODE FACTORY - 1-CLICK INSTANT DEPLOYMENT
echo =========================================================
echo.

echo [1/3] Building production frontend bundle...
cd frontend
call npm run build
if %errorlevel% neq 0 (
    echo [ERROR] Frontend build failed!
    pause
    exit /b %errorlevel%
)
cd ..

echo.
echo [2/3] Publishing directly to GitHub Pages (gh-pages branch)...
npx --yes gh-pages -d frontend/dist -b gh-pages
if %errorlevel% equ 0 (
    echo [SUCCESS] Frontend deployed to GitHub Pages!
) else (
    echo [INFO] Syncing combined branch to origin...
    git push -u origin combined --force
)

echo.
echo [3/3] Deployment complete!
echo =========================================================
echo   Your live application URLs:
echo   - GitHub Pages: https://alien1611.github.io/the-code-factory/
echo   - GitHub Actions: https://github.com/alien1611/the-code-factory/actions
echo   - Vercel (1-Click): https://vercel.com/new (Select alien1611/the-code-factory)
echo =========================================================
echo.
pause
