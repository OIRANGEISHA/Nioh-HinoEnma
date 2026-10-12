# Beta 5.6.2 构建与验证

在 Windows x64、.NET Framework 4.x、Python 3.12 环境安装 `requirements-dev.txt` 后运行：

```powershell
python tools/build_profile.py --check
python tools/check_source.py
python tools/verify_beta562_promotion.py
python tools/run_beta562_regressions.py --report artifacts/beta562-regression-tests.json
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python tools/verify_beta562.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.5.6.2-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify_beta562.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.5.6.2-windows-x64.exe --report artifacts/Release/verification.json
python tools/verify_beta562_ct.py --report artifacts/ct-verification.json
```

版本提升验证器使用从精确实测 FileVersion 1.0.0.76 EXE 独立导出的逐布局摘要，比较全部 82 个运行载荷与原生跳转。新生成 C# 与编译文件另作 12 种地址布局的独立汇编比较；两者合起来验证新构建与实测补丁一致。新 EXE 未重复实机测试，不继承原 EXE 的精确文件测试身份。

当前源码运行全部 240 项回归，拒绝跳过及测试期间源码变化。Debug、Release 各验证 30 项自检、984 次当前载荷和 7536 次历史载荷。CT 验证 984 次三方比较，CE 直接启用未实机测试。修正版的 38 项资源绑定和 49 项原生时钟检查是历史离线证据；私有原生资源夹具没有打包。

[实测记录](living-weapon-beta562-gameplay.json)覆盖完整重启、实际二次载入、太郎太刀 99 启动与自然结束。旧 Boss、无间狱等测试保留原版本身份。忍术道具仍未修复。

发布工作流使用 `.github/scripts/publish_beta562.py`，从固定资产提交取回已在本地离线核对的新版本 EXE，验证当前源码、CT 和所有 Draft 下载后发布。CI 重编译的 EXE 仅作离线验证。源码包来自最终 Git 提交，记录逐文件哈希、提交与 tree；完整包含 EXE、CT、源码和记录。旧 `beta561` 工具保留为历史发布脚本，不适用于当前版本。发布前应先生成 `artifacts/source-checks.json`，并在固定资产 checkout 下执行发布脚本的 `--prepare-only` 模式。
