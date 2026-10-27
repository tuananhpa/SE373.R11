$ErrorActionPreference = 'Stop'
$submissionRoot = $PSScriptRoot
$runtimePython = Join-Path $submissionRoot '.runtime\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $runtimePython)) {
    $runtimePython = Join-Path $submissionRoot 'stage-02-skills\.venv\Scripts\python.exe'
}
if (-not (Test-Path -LiteralPath $runtimePython)) {
    throw 'Chưa có môi trường Python. Chạy uv sync --project stage-02-skills trước.'
}
$modelEnv = Join-Path (Split-Path $submissionRoot -Parent) 'agent-tools-skills-lab\.env'
if (-not (Test-Path -LiteralPath $modelEnv)) { throw 'Không tìm thấy .env của model.' }
& $runtimePython -X utf8 (Join-Path $submissionRoot 'check_tools.py')
if ($LASTEXITCODE -ne 0) { throw 'Kiểm tra tool thất bại.' }
foreach ($stageName in @('stage-00-chat', 'stage-01-files', 'stage-02-skills')) {
    & $runtimePython -X utf8 (Join-Path $submissionRoot 'run_cases.py') $stageName --env $modelEnv
    if ($LASTEXITCODE -ne 0) { throw "Chạy model thất bại ở $stageName." }
}
foreach ($stageName in @('stage-01-files', 'stage-02-skills')) {
    Push-Location (Join-Path $submissionRoot $stageName)
    try {
        & $runtimePython -X utf8 -m pytest tests/test_files.py tests/test_list_files.py tests/test_agent.py tests/test_observer.py -q
        if ($LASTEXITCODE -ne 0) { throw "Tests thất bại ở $stageName." }
        if ($stageName -eq 'stage-02-skills') {
            & $runtimePython -X utf8 -m pytest tests/test_skill_catalog.py -q
            if ($LASTEXITCODE -ne 0) { throw 'Kiểm tra catalog thất bại.' }
        }
    } finally { Pop-Location }
}
& $runtimePython -X utf8 (Join-Path $submissionRoot 'summarize_traces.py')
if ($LASTEXITCODE -ne 0) { throw 'Chưa đủ trace. Xem trace-results.md.' }
Write-Output 'Đã chạy các kiểm tra và tổng hợp trace-results.md. Đối chiếu câu trả lời thực tế với analysis.md trước khi nộp.'
