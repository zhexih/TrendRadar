@echo off
chcp 65001 >nul
echo ===========================================
echo   零售品类社媒热度监控系统
echo   TrendRadar + UAE RSS
echo ===========================================
echo.

echo [1/2] 抓取 UAE 新闻数据...
python "%~dp0scripts\uae_news_fetcher.py"
echo.

echo [2/2] 生成监控简报...
python "%~dp0scripts\retail_monitor.py"
echo.

echo ===========================================
echo   完成！
echo   简报位置: output\reports\retail_monitor_*.md
echo   UAE数据: output\reports\uae_news_*.json
echo ===========================================
pause
