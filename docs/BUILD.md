# Beta 5.6 本地构建

在 Windows 64 位系统准备 Python、requirements-dev.txt 中的依赖及 .NET Framework C# 编译器，运行：

```powershell
python tools/build_profile.py --check
python tools/check_source.py
python tools/run_regressions.py
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python tools/verify_beta56.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.5.6-windows-x64.exe --report artifacts/Release/verification.json
```

当前回归要求239项，其中12项为木灵引导验证，原有资源寿命、连续换层、取消、大蛇、九尾等回归保持。Debug、Release分别要求30项C#检查。CT命名空间12种布局984项比较通过。

`src/hinoenma_abyss_guide.py` 在正常源码链中生成限定EA6E/kind2/instance0/46的兼容。参数、转移和事件来自地址无关的JSON；构建不依赖本机游戏快照或研究目录。只有70号私有载荷在Beta5.5基础上改变，原aura可达代码、另外81个载荷和全部82处原生入口保持。

当前验证工具将82处载荷/跳转与实测热候选在9种ASLR布局下比较，各738项一致。离线证明与正式重启实测记录分开，后者见 `docs/guide-restart-gameplay.json`。旧版本验证和打包脚本保留为历史工具，本版使用上述当前命令。

源码包build-info保存逐文件manifest、构建证明、正式重启验收及EXE哈希。归档不含游戏文件、原始堆转储、凭据或本机依赖。

`version.json` 与离线证明中的重启待验证字段描述构建时状态，不改写原证明和EXE；通过状态由独立验收JSON记录。独立重编译可产生不同EXE哈希，不能继承这个精确文件的游戏实测身份。

GitHub 发布工作流从精确源码提交重建 Debug 和 Release，验证后生成带源码提交、树、逐文件清单和构建证明的源码包。公开发布标签为 `v1.0.0-beta.5.6`；实际提交和 CI 运行链接写入发布包的 build-info。
