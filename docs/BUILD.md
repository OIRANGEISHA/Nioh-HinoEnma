# Beta 6.1.4 构建与发布

版本 `1.0.0-beta.6.1.4`，FileVersion `1.0.0.84`，Windows x64、.NET Framework 4.x。开发使用 Python 3.12 及 `requirements-dev.txt` 中依赖。EXE 使用者无需 Python 或 Cheat Engine。

从仓库根目录执行：

```powershell
python tools/build_profile.py --check
python tools/check_source.py
python tools/verify_beta614_items.py
python tools/run_beta614_regressions.py --report artifacts/beta614/regression-tests.json
./tools/build.ps1 -Configuration Debug -ArtifactRoot artifacts/beta614
./tools/build.ps1 -Configuration Release -ArtifactRoot artifacts/beta614
python tools/verify_beta614.py --exe artifacts/beta614/Debug/Nioh-HinoEnma-1.0.0-beta.6.1.4-windows-x64.exe --report artifacts/beta614/Debug/verification.json
python tools/verify_beta614.py --exe artifacts/beta614/Release/Nioh-HinoEnma-1.0.0-beta.6.1.4-windows-x64.exe --report artifacts/beta614/Release/verification.json
python tools/verify_beta614_ct.py --report artifacts/beta614/ct-verification.json
python tools/package_beta614_local.py --destination <empty-output-directory>
```

若修改源变换，先运行 `python tools/build_profile.py` 生成 C# 和 CT，再执行检查。441 项完整回归使用当前源码；历史测试读取各自冻结基础，新增测试运行最终 84 处载荷的通用分派、投射物补全、连用和受击恢复。测试不访问游戏进程，模拟边界不视为实际伤害或效果验证。

在冻结 Beta 6.1.3 上按实测顺序纳入通用术法、早帧事件和移动后受击修订。与基础相比，10 处原有载荷改变，74 处保持；84 处原生入口、代码分区、目标函数和 `0x69000` 分配保持。要求 12 种布局的 1008 次实测载荷比较、888 次未改载荷比较及 1008 次原生入口比较通过。

Debug／Release 各执行 30 项自检，将 1008 处当前与 7536 处历史载荷同独立汇编结果比较。CT 对原始、数值转换和标签转换后的 1008 处载荷进行三方比较。结果保存在 `artifacts/beta614` 与源码 ZIP 的 `build-info/verification.json`。

源码 ZIP 采用受检本地快照，记录逐文件哈希并读回全部成员；不把本地未提交快照标为 Git 提交。保留旧包、旧 CT、原始实测记录及冻结源码。`general-jutsu-trial.json` 保留打包前原始记录，当前集成结果另见 `validation-beta6.1.4.json`。通用分派的 132 条离线定义不是 132 项效果实测；新 EXE 完整重启与 CT 在 CE 中直接启用尚未实测。

GitHub 发布由版本限定的 `.github/workflows/release.yml` 与 `.github/scripts/publish_beta614.py` 执行。不可变资产提交保存原本地 EXE 与原始校验记录，CI 重建只用于离线比较。发布源码 ZIP 逐成员对应最终 Git 提交；Draft 和公开附件均下载校验，只提供 EXE／源码两个附件。原本地包和历史版本保留；冻结记录的 `local_package_only` 描述原打包阶段，当前发布授权见 `beta614-publication.json`。
