# Beta 6 构建、验证与发布

版本 `1.0.0-beta.6`，适用于 Windows x64、.NET Framework 4.x；开发环境使用 Python 3.12，依赖见 `requirements-dev.txt`。独立 EXE 的使用者无需安装 Python 或 Cheat Engine。

在源码根目录运行：

```powershell
python tools/build_profile.py --check
python tools/check_source.py
python tools/verify_beta6_items.py
python tools/run_beta6_regressions.py --report artifacts/beta6-regression-tests.json
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python tools/verify_beta6.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.6-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify_beta6.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.6-windows-x64.exe --report artifacts/Release/verification.json
python tools/verify_beta6_ct.py --report artifacts/beta6-ct-verification.json
python tools/package_beta6_local.py --destination <empty-output-directory>
```

本版将已实测的切腹短刀、粪球／团扇、四种投掷道具、御箭护符和已测试迟钝符修订整合到 Beta 5.6.3 基础中。版本封装必须保持这些实测载荷的字节身份，并继续保留成长、装备和四类修正 LV 计算。回归、编译载荷比较、CT 三方比较及打包读回的具体数量、文件身份和结果，以本次生成的验证记录为准。

已完成的离线检查：Debug／Release 各通过 30 项自检、12 种当前布局的 984 次载荷比较、108 种历史布局的 7536 次比较；与实测修订的 984 次身份比较全部一致，其中 75 处其他载荷的 900 次比较保持不变。CT 三方比较 984 次、1172 个标签及 26 项拒绝条件检查通过，工具预览显示 Beta 6。

完整回归 291／291 通过，失败、错误和跳过均为 0，用时 126.278 秒，受检源码在运行前后保持不变。新增回归覆盖 82 处载荷 ×12 种布局的编译地址修复，并验证旧版遗漏道具代码区间时会被检查拒绝。报告为 `artifacts/beta6-regression-tests.json`，受检源码树 SHA-256 为 `d0539e6e76bd7063e071b5452ae1dac2e047a167e532af8254cadb782939c42e`。

编译验证发现并修复旧载荷代码区间遗漏：九十九共用载荷新增的道具辅助代码从偏移 `0x4000` 开始，Beta 6 将精确区间 `[16384, 26103]` 纳入 EXE 地址重定位。汇编载荷仍与游戏内实测修订一致；此修复补齐编译后地址转换，不代表新的游戏内测试。

本次只交付本地 EXE 和源码 ZIP，旁附使用说明、键位、校验和与清单。CT 源码包含在源码包中，不额外交付独立 CT 或完整 ZIP。源码包带完整重建源、逐文件清单与离线构建证明，不含游戏文件、存档、原始内存快照、凭据或本机 Python 依赖。打包程序应拒绝覆盖非空输出目录，并校验复制后的 EXE 及源码包全部成员。

`docs/harakiri-gameplay.json`、`docs/dung-fan-gameplay.json`、`docs/four-throwables-gameplay.json` 和 `docs/arrow-sloth-gameplay.json` 保留打包前各次实机测试的原始状态。因此其中的 `release_integration_pending` 等字段描述记录时的阶段；Beta 6 整合与构建结果见当前验证和清单，不能据此改写历史记录。

这批修订已在运行中的游戏里由用户实测确认；新 Beta 6 EXE 仅经过离线检查，尚未完成完整重启实测。公开便携 CPU 测试使用受控的原生函数替代实现，不能代替游戏内验收。其他迟钝符定义、施法受击打断及全部道具／术未全面验证。

本次未提交、推送或发布 GitHub，也未授权沿用旧版本的发布流程。历史 CI、发布脚本及记录保持对应版本身份，不用于宣称 Beta 6 已发布。

GitHub 发布由版本限定的 `.github/workflows/release.yml` 执行。固定资产提交保存原本地 EXE 和原校验记录；CI 重建仅用于离线比较，发布保留原 EXE。源码 ZIP 逐成员对应最终 Git 提交，Draft 和公开附件均下载验证。发布只有 EXE／源码两个附件，不创建访问令牌。冻结 profile 中 `local_package_only` 与旧包记录保留构建时的身份；当前发布授权见 `docs/beta6-publication.json`。
