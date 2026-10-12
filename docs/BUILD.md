# Beta 5.6.1 本地构建

在 Windows 64 位系统准备 Python、`requirements-dev.txt` 中的依赖及 .NET Framework C# 编译器，运行：

```powershell
python tools/build_profile.py --check
python tools/check_source.py
python tools/run_beta561_regressions.py --report artifacts/beta561-regression-tests.json
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python tools/verify_beta561.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.5.6.1-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify_beta561.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.5.6.1-windows-x64.exe --report artifacts/Release/verification.json
python tools/verify_beta561_ct.py --report artifacts/ct-verification.json
```

当前版本保持 82 处原生入口，私有分配为 `0x69000`。数字 9 首次启动时自动发现当前装备的原生 169 动作、主辅动画和事件资源，按当前玩家与装备身份提交绑定；校验失败时不提交。精确起手条件允许一次原生第 0 帧调度，后续启动、消耗和结束由原生事件链处理。固定辅助入口保持原地址，原有资源寿命与附件保护继续生效。

本版 Debug、Release 分别通过 30 项 C# 自检、984 次当前载荷/跳转比较及 7536 次历史载荷比较。另有 17 项真实资源自动绑定 CPU 测试、16 项正式输入集成 CPU 测试，以及 13 项真实原生事件时钟 CPU 测试。输入集成中的原生调用仍采用 ABI 合约；真实事件时钟测试也有停止边界，不能替代完整游戏验证。本版完整回归 240 项全部通过，0 失败、错误和跳过，146 个代码／配置文件的测试前后哈希一致。保留原 239 项并新增 1 项；修正旧版本／布局假设和测试间共享计划污染，使资源寿命与取消检查真正运行在 5.6.1 上。

匹配 CT 已完成离线载荷核对，直接在 CE 中启用未实测。旧版本验证和打包脚本保留为历史工具，本版使用上述命令。

[独立游戏验收](living-weapon-beta561-gameplay.json)记录精确 EXE 的完整重启、自动空绑定启动和自然结束；只读采样与用户视觉确认分别记录。实测使用同一武器和守护灵，item type 11／family 2。大蛇、九尾、无间狱等旧记录保持原版本身份，本轮未重做这些场景。

本版公开发布保留精确本地冷测 EXE。源码归档包含逐文件清单、构建证明、游戏验收及 EXE 哈希，不含游戏文件、原始堆转储、凭据或本机依赖。`version.json` 的 `v1.0.0-beta.5.6.1` 是版本标识；公开发布工作流在验证精确提交、冷测文件和全部 Draft 下载后创建对应标签并发布 Pre-release。独立重编译可能产生不同 EXE 哈希，不能继承精确文件的游戏实测身份。

本地打包命令：`python tools/package_beta561_local.py --destination artifacts/local-beta561`。打包前需通过上述检查；源码包内的 build-info 包含逐文件哈希、240 项回归、两个编译文件和精确游戏验收。当前 `.github/workflows/release.yml` 使用 `.github/scripts/publish_beta561.py` 从不可变资产提交取回原实测 EXE，并另生成精确最终提交的源码包；CI 重编译文件只作离线验证，不作为实测文件发布。

profile 与 version 中部分待验证字段保留原构建时状态，不改写冷测 EXE；通过状态由独立验收 JSON 记录。真实游戏资源／原生代码 CPU 测试使用的私有夹具不包含在公开源码中，其 17／16／13 数量与可重跑的 240 项公开回归分开记录。
