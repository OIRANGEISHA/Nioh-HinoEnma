# Beta 6.1.3 构建、验证与发布

版本 `1.0.0-beta.6.1.3`，FileVersion `1.0.0.83`，Windows x64、.NET Framework 4.x。开发使用 Python 3.12 及 `requirements-dev.txt` 中依赖。EXE 使用者无需 Python 或 Cheat Engine。

从仓库根目录执行：

```powershell
python tools/build_profile.py --check
python tools/check_source.py
python tools/verify_beta613_items.py
python tools/run_beta613_regressions.py --report artifacts/beta613/regression-tests.json
./tools/build.ps1 -Configuration Debug -ArtifactRoot artifacts/beta613
./tools/build.ps1 -Configuration Release -ArtifactRoot artifacts/beta613
python tools/verify_beta613.py --exe artifacts/beta613/Debug/Nioh-HinoEnma-1.0.0-beta.6.1.3-windows-x64.exe --report artifacts/beta613/Debug/verification.json
python tools/verify_beta613.py --exe artifacts/beta613/Release/Nioh-HinoEnma-1.0.0-beta.6.1.3-windows-x64.exe --report artifacts/beta613/Release/verification.json
python tools/verify_beta613_ct.py --report artifacts/beta613/ct-verification.json
python tools/package_beta613_local.py --destination <empty-output-directory>
```

若修改源变换，先运行 `python tools/build_profile.py` 生成 C# 和 CT，再执行检查。409 项完整回归使用当前源码；旧版 CPU 测试从冻结的 Beta 6.1.2 或更早基础重建，不能把当前发布包再次套用试验变换。历史试验测试仅更换输入加载器以读取原版冻结基础；其原始证明与哈希保留。最终 84 处载荷另执行宿心、九种符与散变复用行为、ABI 和拒绝条件。

在冻结 Beta 6.1.2 上按实测顺序纳入粘液罐／散变符、散变复用修订 2、九种符及宿心解放符。与基础相比，10 处原有载荷改变，72 处保持；新增两个限定于玩家宿心解放符的装备读取入口，总计 84 处。保留原有 82 处原生入口与 `0x69000` 分配，将两段既有空余代码尾部分给新读取入口。要求 12 种布局的 1008 次实测载荷比较、864 次未改载荷比较及 984 次原有入口比较通过。

Debug／Release 各执行 30 项自检，并将 1008 处当前和 7536 处历史载荷与独立汇编结果比较。CT 对原始、数值转换和标签转换后的 1008 处载荷进行三方比较。完成结果保存在本次 `artifacts/beta613` 报告与源码 ZIP 的 `build-info/verification.json`。

源码 ZIP 采用受检本地快照，逐文件记录哈希并读回全部成员；来源不标为未创建的 Git 提交。保留旧包、旧 CT、原始实测记录及冻结源码。当前 EXE 的完整重启实测尚未进行，CT 在 CE 中直接启用亦未实测。护灵招来符连续记录的读取限制见 `guardian-sludge-items-trial.json`；已知限制不得用离线检查覆盖。

本次实际检查数量、结果及文件身份见 `validation-beta6.1.3.json`，不沿用旧版报告的通过结果。

GitHub 发布由版本限定的 `.github/workflows/release.yml` 与 `.github/scripts/publish_beta613.py` 执行。固定资产提交保存原本地 EXE 和原校验记录，CI 重建仅用于离线比较，发布保留原 EXE。公开源码 ZIP 逐成员对应最终 Git 提交，Draft 和公开附件均下载验证，附件仅 EXE／源码两个。不创建新访问令牌。原本地源码 ZIP 与冻结记录保留；`local_package_only` 等字段描述原打包阶段，本次发布授权见 `docs/beta613-publication.json`。
