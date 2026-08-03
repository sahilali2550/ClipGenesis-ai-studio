@echo off
cd /d "%~dp0"
set "PYTHONPATH=%~dp0"
set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:32
set CUDNN_LOGINFO_DBG=0
set CHATTERBOX_CFG_WEIGHT=0.2
set CHATTERBOX_CHUNK_THRESHOLD=800

rem Add cuDNN to path if conda env style bin exists in venv
if exist ".venv\Lib\site-packages\nvidia\cudnn\bin" (
    set "PATH=%~dp0.venv\Lib\site-packages\nvidia\cudnn\bin;%PATH%"
)

.venv\Scripts\python.exe -m streamlit run .\webui\Main.py --browser.gatherUsageStats=False --server.enableCORS=True
