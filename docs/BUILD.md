# Beta 6.2 构建与发布

版本 `1.0.0-beta.6.2`，FileVersion `1.0.0.85`，Windows x64、.NET Framework 4.x。开发环境为 Python 3.12 及 `requirements-dev.txt` 中依赖；EXE 使用者无需 Python 或 Cheat Engine。

```powershell
python tools/build_profile.py --check
python tools/check_source.py
python tools/verify_beta62_items.py
python tools/run_beta62_regressions.py --report artifacts/beta62/regression-tests.json
./tools/build.ps1 -Configuration Debug -ArtifactRoot artifacts/beta62
./tools/build.ps1 -Configuration Release -ArtifactRoot artifacts/beta62
python tools/verify_beta62.py --exe artifacts/beta62/Debug/Nioh-HinoEnma-1.0.0-beta.6.2-windows-x64.exe --report artifacts/beta62/Debug/verification.json
python tools/verify_beta62.py --exe artifacts/beta62/Release/Nioh-HinoEnma-1.0.0-beta.6.2-windows-x64.exe --report artifacts/beta62/Release/verification.json
python tools/verify_beta62_ct.py --report artifacts/beta62/ct-verification.json
python tools/package_beta62_local.py --destination <empty-output-directory>
```

修改源变换后先运行 `python tools/build_profile.py` 生成 C# 和 CT，再检查。459 项完整回归包含历史冻结基础和最终 86 处载荷的 CPU 验证，不访问游戏。相对 Beta 6.1.4，9 处原载荷改变、75 处载荷保持，新增 2 处宿心升华爱用度读取。原 84 处入口保持，旧代码槽的空白区分出两个新槽，分配仍为 `0x69000`。

Debug／Release 各 30 项自检；12 种布局下分别比较 1032 处当前载荷、7536 处历史载荷，以及 1032 次 CT 三方比较。正式载荷逐项匹配已实测候选。原试验记录保留原始身份，当前集成记录见 `validation-beta6.2.json`。

本地源码 ZIP 逐文件记录哈希、读回检查。GitHub 由版本限定工作流和 `publish_beta62.py` 发布，保留本地验证 EXE 的原字节，源码 ZIP 对应最终 Git 提交，Draft 与公开附件均下载核验。Release 仅 EXE／源码 ZIP，说明、CT、验证记录在源码包内。

木灵变身及宿心升华已实测。木灵受击分支仅离线检查；新 EXE 的完整重启实测及 CT 直接启用尚未进行。部分忍术／阴阳术和道具仍未修复或验证。
