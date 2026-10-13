# Beta 6.1 构建、验证与本地打包

版本 `1.0.0-beta.6.1`，FileVersion `1.0.0.80`，适用于 Windows x64、.NET Framework 4.x；开发环境使用 Python 3.12，依赖见 `requirements-dev.txt`。独立 EXE 的使用者无需安装 Python 或 Cheat Engine。

在源码根目录运行：

```powershell
python tools/build_profile.py --check
python tools/check_source.py
python tools/verify_beta61_items.py
python tools/run_beta61_regressions.py --report artifacts/beta61-regression-tests.json
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python tools/verify_beta61.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.6.1-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify_beta61.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.6.1-windows-x64.exe --report artifacts/Release/verification.json
python tools/verify_beta61_ct.py --report artifacts/beta61-ct-verification.json
python tools/package_beta61_local.py --destination <empty-output-directory>
```

本版在冻结 Beta 6 基础上加入风箭符 `26116`、克金符 `44930` 和火炎龙术卷轴 `44607` 的已实测修订。只改变 `HE_InputA`、`HE_InputB` 和 `HE_LivingWeaponDigitNine` 的载荷，保留其余 79 处；补丁总数仍为 82，分配仍为 `0x69000`。原生成长、装备和四类修正 LV 计算保持不变。

版本封装与编译后载荷必须匹配运行中已实测候选，并覆盖 12 种当前地址布局；保留其他 79 处载荷和全部原生入口。九十九共用载荷的道具辅助代码从偏移 `0x4000` 开始，当前精确重定位区间为 `[16384, 32164]`，须覆盖新增施法辅助及资源检查代码。辅助资源检查与克金符公共／私有动作区分也纳入便携 CPU 回归。

构建核对发现，新载荷长 32164 字节，超过启动器原有的 `0x7000` 字节完整读取上限。启动器据当前代码槽容量将上限调整到 `0x8000`，仍以 `0x1000` 分块读取并拒绝不完整读取；边界、超限和部分读取检查须通过，确保安装后能核对完整载荷。

完成情况以本次 `artifacts/beta61-regression-tests.json`、`artifacts/beta61-item-equivalence.json`、`artifacts/beta61-ct-verification.json` 以及 Debug／Release 的 `verification.json` 为准。记录完整回归、C# 自检、当前和历史载荷比较、实测身份比较、CT 三方比较及包内成员读回结果；旧版报告中的完成数不代表本版检查已经执行。

本地包的主要文件为 EXE 和源码 ZIP，旁附使用说明、键位、校验和与清单。CT 源码和离线验证记录包含在源码包中，不额外生成独立 CT 或完整 ZIP。源码包保留完整重建源、逐文件清单和本地构建来源，排除游戏资源、存档、原始内存快照、凭据及本机依赖。打包程序拒绝覆盖非空目录，并校验复制后的 EXE 及每个 ZIP 成员。

新三项修订的次数扣除、效果及使用后移动、J／I／数字 5 已由用户在运行中的游戏里确认正常，记录另确认原生施法及火龙收招。新 EXE 的离线检查不等于该 EXE 的完整重启实测。公开便携 CPU 测试使用受控原生函数替代实现；其他同名定义、施法受击打断及所有场景未全面验证。

历史 Beta 6 与更早版本的实测、发布记录和冻结源码保持原始身份。用户随后授权公开发布；本版授权见 `beta61-publication.json`，发布工作流使用 `.github/scripts/publish_beta61.py`。它固定原本地 EXE 身份，重新验证当前源码和构建，按最终 Git 提交生成源码包，并下载校验两个附件后发布 Pre-release；原本地包与历史记录保持不变。

本次完成记录：318／318 项回归通过，失败、错误及跳过均为 0，受检源码前后不变；Debug／Release 各通过 30 项自检、984 次当前载荷和 7536 次历史载荷比较。与已实测候选的 984 次身份比较一致，其他 79 处载荷的 948 次比较保持不变；CT 三方比较 984 次、1208 个唯一标签及源码的 26 项拒绝条件检查通过。完整生成源检查通过，工具窗口预览显示 Beta 6.1。详情见 `validation-beta6.1.json`，源码 ZIP 的 `build-info/verification.json` 保留完整报告。
