# Beta5.6.3 构建、验证与发布

Windows x64、.NET Framework4.x、Python3.12；Python依赖见requirements-dev.txt。

```powershell
python tools/build_profile.py --check
python tools/check_source.py
python tools/verify_beta563_growth.py
python tools/run_beta563_regressions.py --report artifacts/beta563-regression-tests.json
./tools/build.ps1 -Configuration Debug
./tools/build.ps1 -Configuration Release
python tools/verify_beta563.py --exe artifacts/Debug/Nioh-HinoEnma-1.0.0-beta.5.6.3-windows-x64.exe --report artifacts/Debug/verification.json
python tools/verify_beta563.py --exe artifacts/Release/Nioh-HinoEnma-1.0.0-beta.5.6.3-windows-x64.exe --report artifacts/Release/verification.json
python tools/verify_beta563_ct.py --report artifacts/ct-verification.json
python tools/package_beta563_local.py --destination <empty-output-directory>
```

成长源模块保持实机测试的原字节身份；正式源生成链只增加版本封装。Beta5.6.2历史生成链及冻结配置保留；12种布局核对只有属性载荷改变，其余81处载荷、全部原生跳转不变。源码包含完整重建源、逐文件清单和离线构建验证；不含游戏文件、存档、内存快照、凭据或本机Python依赖。

原生游戏叶函数的750等级和25组Focus分配检查是本地研究证据，不能从不带游戏资源的源码包重跑；公开便携CPU测试使用明确的ABI替代函数。当前新EXE冷启动实机验证未重复。此前版本的CI发布脚本和证据保持原版本身份。当前使用版本限定的 publish_beta563.py；GitHub Actions 从固定资产提交提取原本地EXE，以最终Git提交生成源码包，检验Draft和公开附件。CI重新构建的EXE仅作离线证明，不替换原本地文件。

发布资产来源固定在docs/beta563-publication.json。发布程序先核对原EXE与原始本地记录，再针对当前提交运行全部检查；源码包保留所有构建源与build-info证明，完整包包含EXE、源码、CT、使用/键位说明及验证记录。公开EXE无需Python或CE。
