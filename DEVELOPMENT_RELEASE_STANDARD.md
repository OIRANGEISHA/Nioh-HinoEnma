# Beta 6.1.4 当前公开发布范围

2026-10-16，用户要求 push 到 GitHub，沿用此前直接发布授权。发布 v1.0.0-beta.6.1.4 Pre-release（latest=false），仅提供已校验的原本地 EXE 和最终 Git 提交的完整源码 ZIP。使用说明、键位、CT、验证记录放入源码包，明确部分忍术／阴阳术仍未修复或验证，不把 132 条离线定义覆盖写成全部实测。保留本地包、历史标签和附件。

沿用连接器 Git Data API 与版本限定 GitHub Actions，只使用既有工作流令牌。固定 EXE 与原始验证记录的资产提交，运行 441 项回归、Debug／Release 各 30 项自检、1008 当前／7536 历史载荷及 CT 三方比较。Draft 与公开附件均下载验证，源码逐个 Git blob 核对。新 EXE 的完整重启实测尚未进行。

当前授权与精确身份见 docs/beta614-publication.json。以下为历史阶段记录。

---

# Beta 6.1.3 历史公开发布范围

2026-10-15，用户明确要求推送 GitHub，授权直接完成发布且不再询问。推送现有仓库 main，并发布 v1.0.0-beta.6.1.3 Pre-release（latest=false）。附件仅原本地 EXE 和最终提交源码 ZIP；说明、键位、CT 与验证记录放入源码包。说明须明确“仍有部分阴阳术的使用尚未修复”。保留原本地包、历史标签与附件。

沿用连接器 Git Data API 与版本限定 GitHub Actions，仅用现有工作流令牌。固定原 EXE 和原始证明的不可变资产提交，核对最终源码 tree，完整 409 项回归、Debug／Release 各 30 自检、1008 当前与 7536 历史载荷、1008 实测载荷及 CT 三方比较。Draft 和公开附件均下载验证，源码逐个 Git blob 核对。发布不更改游戏或运行载荷。

新 EXE 未完整重启实测，热接入反馈与离线结果分别保留。冻结 profile 和原验证报告保持原始身份；当前授权由 docs/beta613-publication.json 记录。下列历史本地范围不限制本次授权发布。

---

# Beta 6.1.3 历史本地打包范围

2026-10-15，用户要求检查正常后，将宿心解放符及此前未打包改动一起打包为 Beta 6.1.3。FileVersion 1.0.0.83，交付 release/Beta6.1.3 的独立 EXE 与完整本地源码 ZIP，旁附使用说明、键位和校验清单。本次仅本地打包，保留全部旧包和原始试验证据。

冻结 Beta 6.1.2，依次纳入粘液罐／散变符、散变连续使用修订 2、九种符、宿心解放符的已实测源码。发布包装只更新版本和确认元数据，全部 84 处载荷须与实测候选一致。相较 Beta 6.1.2，10 处原有载荷改变、72 处不变；新增两处宿心解放符原生装备读取入口，既有入口不移动，分配保持 0x69000。实际 Boss 装备保持；光刃、次数及当前武器爱用度仍由原生流程处理。

要求完整 409 项回归、Debug／Release 各 30 项自检、各 1008 次当前和 7536 次历史载荷比较、1008 次实测候选身份比较、864 次未改载荷比较以及 CT 三方 1008 次比较。最终载荷另执行宿心、九种符和散变复用行为测试。源码 ZIP 全部成员读回；原始试验文件的旧状态与哈希保持。本次结果以 artifacts/beta613 和 validation-beta6.1.3.json 为准，新 EXE 尚未完整重启实测。

---

# Beta 6.1.2 历史本地打包范围

2026-10-15，用户要求“先打包吧”。现有 Beta 6.1.1 保留，新修复按 Beta 6.1.2、FileVersion 1.0.0.82 打包至 release/Beta6.1.2，交付独立 EXE 与完整本地源码 ZIP，并附说明、键位和校验清单。本次仅本地打包。

冻结 Beta 6.1.1 基础，原样纳入已实测的五种禁属性晴明符变换。仅 HE_LivingWeaponDigitNine 的既有代码槽改变，其余 81 处载荷不变，82 个原生入口和 0x69000 分配保持。五种原生增益及三次禁火符受击恢复有实测依据；无显示数量，不以扣除数量验收。包装仅更新版本及确认元数据，保留原试验记录身份。

执行完整 369 项回归、Debug／Release 各 30 项自检、12 布局下 984 次当前载荷与 7536 次历史载荷比较、984 次实测候选身份比较、972 次未改载荷比较及 984 次 CT 三方比较。源码包逐成员读回。具体结果以 artifacts/beta612 和本次 validation 记录为准，不沿用旧版通过结果。新 EXE 尚未完整重启实测。

---

# Beta 6.1.1 历史本地打包范围

2026-10-15，用户要求“先打一个 beta6.1.1 的包，把做好的修复纳入”。本次版本为 `1.0.0-beta.6.1.1`、FileVersion `1.0.0.81`，交付到 `release/Beta6.1.1`。交付独立 Windows x64 EXE 与完整本地源码 ZIP，旁附使用说明、键位、校验和及清单，CT 放入源码包。本次只做本地打包，保留历史包和证据身份。

冻结 Beta 6.1 基础，按原顺序整合施法事件补偿、道具受击公共动作查找、移动后连续施法查找及护灵招来符／污泥罐入口。四份实测源码保持字节身份，发布包装只更改元数据；82 处补丁、`0x69000` 分配及原生入口不变，8 处载荷改变，其他 74 处保持一致。保留第一栏数字 2 的道具位、成长、装备和四类修正 LV 规则。

要求 355 项完整回归、Debug／Release 各 30 项自检、12 布局的 984 次当前载荷比较与 7536 次历史载荷比较、984 次实测候选身份比较、888 次未改载荷比较及 984 次 CT 三方比较。以 `artifacts/beta611` 本次实际报告为准。使用 `verify_beta611.py`、`verify_beta611_items.py`、`verify_beta611_ct.py`、`run_beta611_regressions.py`、`package_beta611_local.py`。源码 ZIP 全部成员和复制后的 EXE 读回验证，标记为受检本地快照。

实测与离线证据分开：风箭／克金的效果、已测受击恢复、连续使用和新增两道具已获用户确认；未逐个实测全部受击分支。护灵招来符连续记录在召唤物所有者检查处中止，保留不完整记录事实，用独立只读数量／补丁快照及用户反馈交叉验证。新 EXE 尚未完整重启实测。历史报告中的 `release_exe_updated: false` 保留原记录时身份。

---

# Beta 6.1 历史公开发布范围

2026-10-13，用户明确要求“先push beta6.1到github吧”，授权推送到现有仓库 main，发布 v1.0.0-beta.6.1 Pre-release（latest=false）。Release 仅含原本地 EXE 和最终提交源码 ZIP 两个附件；使用说明、键位、CT 与验证记录放入源码包，校验和写入发布说明。保留原本地包和全部历史标签、附件。

沿用 GitHub 连接器 Git Data API 与版本限定的 GitHub Actions 发布，使用现有工作流令牌，不创建新令牌。核对本地与远端 tree、不可变 EXE 和原始本地证明；要求当前 318 项回归、Debug／Release 各 30 自检、984 当前与 7536 历史载荷比较、984 实测身份和 CT 三方比较通过，其他 79 处载荷的 948 次比较保持一致。下载后验证两个附件，并逐个 Git blob 核对源码 ZIP。

新 EXE 的完整重启实测尚未完成，运行中的三项术法实测与离线检查分别记录。冻结 profile、原包及历史报告中的 local_package_only 等字段保留原始身份；本次公开发布授权由 docs/beta61-publication.json 记录。以下原本地范围不限制本次已授权发布。

---

# Beta 6.1 历史本地范围

2026-10-13，用户要求“打包吧，版本号beta6.1”。当前版本为 `1.0.0-beta.6.1`、FileVersion `1.0.0.80`，保留 82 处补丁与 `0x69000` 分配。本次仅本地构建、验证与交付到 `release/Beta6.1`，不提交、推送或发布 GitHub，不创建标签或 Release，不替换历史文件。以下发布授权分别属于对应历史版本。

交付独立 Windows x64 EXE 与完整源码 ZIP，旁附使用说明、键位、校验和及清单；CT 位于源码包内。源码 ZIP 使用本次受检本地快照和逐文件清单，不能宣称来自尚未创建的提交或已公开发布。排除游戏资源、存档、原始内存快照、凭据和本地依赖；打包后读回验证 EXE 与源码包全部成员，拒绝覆盖非空输出目录。

将风箭符 `26116`、克金符 `44930`、火炎龙术卷轴 `44607` 的已实测修订封装到冻结 Beta 6 基础中。仅 `HE_InputA`、`HE_InputB` 和 `HE_LivingWeaponDigitNine` 载荷变更，其余 79 处保持原样；输入入口、82 处原生补丁地址、分配及保护数据不变。保留原生施法、次数消耗、主辅事件和火龙收招，克金符按所属请求区分公共及私有同编号动作。成长、装备、四类修正 LV 及第一栏数字 2 的道具快捷位保持。

三项效果、次数扣除及使用后移动、J／I／数字 5 已由用户在运行中的游戏里确认正常。运行中修订与新 EXE 分开记录，新 EXE 未完整重启实测；其他术法定义、施法受击打断及全部场景未全面验证。保留原始试验源码和证据身份，新增发布包装不得改写历史实测记录。

使用 `verify_beta61.py`、`verify_beta61_items.py`、`verify_beta61_ct.py`、`run_beta61_regressions.py`、`package_beta61_local.py` 及当前 BUILD.md 验证。完整回归、Debug／Release 自检、当前及历史载荷、与实测候选的身份比较、CT 三方比较和源码包读回须全部通过。要求 82 处载荷 ×12 种当前布局完整比较，并验证其余 79 处 ×12 种布局不变；具体完成数量、哈希及结果以本次实际报告为准，不沿用旧版完成数。

---

# Beta 6 历史公开发布范围

2026-10-13，用户在本地 Beta 6 打包完成后明确要求“push到github上吧”，授权推送到现有仓库 main，并发布 v1.0.0-beta.6 Pre-release（latest=false）。仅发布原本地 EXE 与最终提交源码 ZIP 两个附件；说明、键位、CT 与验证记录在源码包内，校验和写入发布说明。保留原本地包和全部历史标签、附件。

通过 GitHub 连接器 Git Data API 推送，验证本地与远端 tree 一致并同步检出；版本限定的 GitHub Actions 只用现有工作流令牌发布。要求当前 291 项回归、Debug／Release 各 30 自检、984 当前和 7536 历史载荷比较、984 实测载荷身份和 CT 三方比较通过。上传后逐个下载附件验证，源码逐个 Git blob 校验。保留十种道具的原始热接入实测证据；新 EXE 尚未经过完整重启实机验收，不把离线检查写成实机结果。

冻结运行 profile 与原包的 local_package_only 等字段记录原始打包阶段，不能改写；本次授权以 docs/beta6-publication.json 为准。下面是历史本地范围，不限制本次已授权发布。

---

# Beta 6 历史本地范围

2026-10-13，用户要求将已实测道具修订打包为 Beta 6。当前版本为 `1.0.0-beta.6`、FileVersion `1.0.0.79`，保留 82 处补丁与 `0x69000` 分配。本次仅本地构建、验证与交付，不提交、推送或发布 GitHub，不创建标签或 Release，也不替换历史资产。下面 Beta 5.6.3 及更早版本的发布授权仅属于相应历史版本，不延用到 Beta 6。

交付独立 Windows x64 EXE 与完整源码 ZIP，旁附使用说明、键位、校验记录、SHA-256 与清单。CT 包含在源码包内，不额外交付独立 CT 或完整 ZIP。源码包采用本次受检的本地文件快照与逐文件清单；未提交的本地包不得宣称来自新的 Git 提交或已公开发布。保留全部重建源与离线证明，排除游戏资源、存档、原始内存快照、凭据及本地依赖。

整合切腹短刀、粪球／高贵的粪球／天狗团扇、石头／火药弹／焙烙弹／焚火油壶、御箭护符和已测试迟钝符定义 4998。两符通过精确所属请求解决公共动作 41／42 与私有动作同编号冲突，保留原生增益、投射物、道具和术次数消耗。其他迟钝符定义、其他术及全部道具兼容不得据此宣称通过。成长仍为 0—750 级映射 1—4525 档，401 级起 Boss 基础生命 ×2、主攻击 ×1.2，然后叠加成长、装备及四类修正 LV；道具快捷位保持第一栏数字 2。

这批修订已在运行中的游戏里由用户实测确认，新 Beta 6 EXE 仅经过离线检查、尚未完整重启实测。四份道具 gameplay 报告保留原始试验时的状态；Beta 6 整合后的源码、编译载荷、CT 与打包结果应另记，不能改写历史实测身份。回归测试、Debug／Release 自检、当前与历史载荷比较及包内每个成员读回须全部通过；使用 `verify_beta6.py`、`verify_beta6_items.py`、`verify_beta6_ct.py`、`run_beta6_regressions.py`、`package_beta6_local.py` 与当前 BUILD.md。具体数量和哈希以本次实际报告为准，不沿用 Beta 5.6.3 的完成数。本次不要求用户重复实机测试，也不把离线通过记为完整重启验收。

---

# Beta5.6.3 历史发布范围

2026-10-13，用户在本地打包完成后要求“push到github”，授权将Beta5.6.3源码推送到现有公开仓库main并发布v1.0.0-beta.5.6.3 Pre-release，latest=false。沿用上版六附件：原本地EXE、CT、最终提交的源码ZIP、完整ZIP、校验和、清单；不替换旧标签或资产。通过GitHub连接器Git Data API传输，并验证本地与远端tree一致、同步本地干净检出。

FileVersion1.0.0.78，82处补丁、0x69000分配。0—750级映射1—4525档，401级起Boss生命×2、主攻击×1.2；原生成长、装备及四类修正LV继续叠加。只有属性载荷改变，其他81处载荷不变。热接入和装备刷新已在750级实测确认；新EXE未冷启动实机验收，非零体力/防御/幸运修正实机分配和实际跨400/401升级仍待验证。

要求248项当前源码回归、两种构建各30项自检、984当前及7536历史载荷比较、CT三方984次比较、与实测热载荷984次身份比较。原本地EXE与原验证记录固定保存；源码ZIP来自最终提交的每个Git blob，Draft与公开附件逐个下载校验。历史原始证据中的github_published:false表示记录时状态，不覆盖本次授权与公开结果。忍术道具及部分非关键道具仍未修复。以下为历史范围。

---

# Beta5.6.3 当前本地范围

2026-10-13，用户要求打包Beta5.6.3到release文件夹。本次仅本地构建与交付，不推送或发布GitHub，不改写历史资产。FileVersion1.0.0.78，82处载荷，0x69000分配。成长模块与已实测热修订逐字节等同；新EXE没有冷启动实机验收。验证248项源码回归、Debug/Release各30自检、984当前/7536历史载荷比较及CT三方比较；每个源码/完整包成员读回校验。以下内容保留对应历史范围。

---

# Beta 5.6.2 当前发布范围

2026-10-13，用户要求“版本号改为beta5.6.2，然后推送到github”。本次发布换存档计数及武器资源兼容修复到现有公开仓库 main，并沿用上版附件形式发布 v1.0.0-beta.5.6.2 Pre-release，latest=false：EXE、CT、源码 ZIP、完整 ZIP、校验和与清单。FileVersion 为 1.0.0.77，82 处补丁、0x69000 分配。保留全部旧标签、发布、附件及原始实测证据。

精确实测文件是修正版 FileVersion 1.0.0.76，已完整重启并实际第二次载入，太郎太刀 99 全流程正常。Beta5.6.2 是版本提升后的新构建，需验证全部载荷与实测文件在 12 种地址布局下一致，不声称新 EXE 重做了实机验收。当前源码要求 240 回归、两个构建各 30 自检、984 当前及 7536 历史载荷比较；CT、源码 ZIP、Draft 和公开附件读回核对。GitHub Git Data API 用于已授权推送，记录方法并同步本地干净检出。忍术道具无法使用仍为已知问题。

以下条目均为对应历史版本的授权与验证范围；当前说明以本段、README 和 Beta5.6.2 发布说明为准。

---

# Beta 5.6 当前发布范围

2026-10-12 用户要求“beta版本改成beta5.6，推送到github”，授权将已验收的木灵引导、无间狱连续换层及资源持有修复以 Beta5.6 推送到现有公开仓库 OIRANGEISHA/Nioh-HinoEnma 的 main，并发布 v1.0.0-beta.5.6 预发布版，附件为独立 Windows x64 EXE 和完整源码 ZIP，latest=false。版本1.0.0-beta.5.6、file1.0.0.73、CT Beta5_6，82处补丁和0x55000分配。已验收Beta5.5.1的实机证据及原EXE哈希保持；Beta5.6是版本标记更新，不声称此精确EXE重新经过实机测试。

要求239项源码回归、Debug和Release各30项离线检查、984项当前载荷比较及7536项历史比较；在9种ASLR布局中与热候选、已验收Beta5.5.1逐处比较载荷和跳转。源码提交和树需精确匹配，源码ZIP每个成员、CRC、元数据、构建证明以及上传后下载的两项附件均校验。GitHub连接器Git对象传输若用于推送，应记录方式并同步本地干净检出；Actions构建和发布身份是github-actions[bot]。历史标签、附件、原始验收记录保持。

下面各版本记录描述当时范围，不代表这些旧版未修复问题在Beta5.6仍未修复，也不代表旧版每条实机测试都重新执行。当前状态见README、CHANGELOG和本版发布说明。

---
# Beta 5.5 当前范围

2026-10-12 用户要求“弄好这没问题的话就先打包为beta5.5”，授权当前修复的本地交付。保留完整重启候选的82处载荷，版本为1.0.0-beta.5.5、file1.0.0.71。新EXE的离线证明与候选实机证据区分记录；源码ZIP及EXE复制后逐文件读回。坐船仍待单独复测和修复。没有新增此版本的公开推送或发布操作。

以下记录保留各历史版本当时的授权和验收范围，不作为Beta5.5已经完成CI发布或旧版全部测试已重复执行的证明。

---

# Nioh Hino-Enma development and release standard

Current work: **1.0.0-beta.5.4.1**, file **1.0.0.68**. Local verification, packaging and technical records are complete. On 2026-10-11 (Asia/Shanghai), the user authorized the reviewed source push to `main`, and after that CI passed requested the actual GitHub Release. This current authorization includes the Beta 5.4.1 annotated tag, inspected Draft and publication as Pre-release with latest=false and exactly the Windows x64 EXE and complete source ZIP. Use [the current build instructions](docs/BUILD.md) and `tools/package.py` from an exact clean reviewed commit. The version-scoped Actions publisher permits this one Beta 5.4.1 publication after all 177 regressions, three source proofs, both build verifications, source ZIP and downloaded asset readback pass. Preserve the original local snapshot/EXE and all historical tags/assets. Record CI-built results separately from the locally gameplay-tested EXE. The Beta 5.3.2 authorization remains historical; future versions require their own authorization.

## Current Beta 5.4.2 authorization

On 2026-10-11 (Asia/Shanghai), after the new exact local EXE completed Nine Tails execution and story in a fully restarted game and the user confirmed restored movement/menu control, the user requested pushing Beta 5.4.2 to the existing GitHub repository. This authorizes the complete source and repair records on main and the new v1.0.0-beta.5.4.2 annotated tag/inspected Draft/Pre-release with exactly the standalone x64 EXE and complete source ZIP, latest=false. The source uses file version 1.0.0.69, CT Beta5_4_2, 81 hooks, allocation 0x51000 and an independent 512-byte Nine Tails binding. Keep the full original eight Orochi bodies and 73 identical unrelated payloads. Require 203 regressions, four source proofs, 29 self-checks and 972 current/6564 historical comparisons per build (12/96 layouts), exact source tree and downloaded asset readback. The original local package and earlier public tags/assets retain their identities. API fallback must record its use, match local/remote tree hashes and synchronize the clean checkout. Future versions require their own authorization.

Known issue added at the user's request: taking the boat in the Abyss crashes the game. This remains unfixed and deferred; Beta 5.4.2 does not claim a cause or repair for it. Current new EXE gameplay evidence includes user confirmations and VM_READ-only native post-execution state; the earlier frame-by-frame clock belongs to the scene candidate. The CI-built EXE has its own hash and offline proof, not a new gameplay confirmation. These current controls supersede the older current-work paragraph above; the following Beta 5.4.1 controls remain historical.

The user also requested recording the next-floor Abyss interaction completing its progress but having no effect. This remains unfixed and deferred for later repair; do not expand the current release into an unverified fix for either Abyss issue.

## Beta 5.4.1 local verification controls

- Complete 177 source regressions, the frozen 59 menu/cold-start tests and the 34 synthetic execution tests. Record actual passing reports and exact source hashes. Preserve all previous71 payloads and patches across 12 ASLR layouts; retain the immutable Beta 5.2 basis.
- Build Debug and optimized x64 Release. Each requires 29 C# checks, 972 current payload comparisons across 12 layouts and 5592 complete historical payload comparisons across 84 layouts. Keep current and historical counts distinct.
- Preserve eight writable, non-executable data pages and non-overlapping code slots. Reject incomplete/mixed installations and recognize all seven historical installation identities read-only: 55/59/60/70/71/71/80 hooks. Check complete native instruction-pointer and saved-return exclusions for ten execution/resource/geometry/query frames, including the full query86 frame and correct late no-hit epilogue.
- Read current owned native action, motion and main/auxiliary event resources with bounded lookup. Do not embed recorded instance, stack, geometry or heap addresses. Preserve original heavy input, native kill/mission progression and terminal recovery; no direct actor, HP, mission or save writes for this repair.
- Keep scene-bound gameplay evidence separate from final dynamic-binding EXE verification. The exact Release EXE passed a complete game-process restart, main-menu enable and final Orochi execution on `1DC1C / 19569 / 3203`; the user confirmed the kill, continued story and restored control. All 81 hooks were verified with no diagnostic hook or temporary patch. Record its SHA-256 in the validation and package evidence. Eight full head battles remain untested individually, the earlier `8F795` failure cause remains unproven, and Nine Tails needs separate native-chain/resource/event/cleanup evidence. Retain failed approaches and numerical freeze causes in the technical record.
- Verify every local source ZIP member and the copied EXE after packaging. Include the debugging record, usage, rebuild instructions, source manifest, three portable proofs, complete regressions and both build reports. Do not replace historical assets or records.

Adapted for this Windows game tool from [RapidBench DEVELOPMENT_RELEASE_STANDARD.md](https://github.com/OIRANGEISHA/Rapidbench/blob/main/DEVELOPMENT_RELEASE_STANDARD.md), document 1.1. Android packaging, ABI splits, APK signing and benchmark scoring requirements do not apply to this project.

## Required publication controls

- Use Semantic Versioning with increasing Beta/Hotfix identifiers and immutable public tags. The previously published version is **1.0.0-beta.5.3.1**, tag **v1.0.0-beta.5.3.1**, file version **1.0.0.65**. It adds native preview mist and reload-safe camera framing to Beta 5.3, retaining private profile 0.60 and inherent element revision 2. The file version is not a private profile version. Beta releases are GitHub Pre-releases with latest=false. Prior tags, attachments and historical committed records remain unchanged. The specifically authorized historical Beta 5.1 replacement below was the sole exception to retaining its superseded attachments.
- Release Owner: **OIRANGEISHA**. Record the actual source author/tagger and upload identity. The owner-authorized Actions publisher may prepare tag, draft and assets; its uploads must be identified as github-actions[bot].
- Use Conventional Commits and record the exact source commit/tree with a clean reviewed checkout. An API transport fallback must compare local/remote tree hashes and record its use.
- Keep requirements, compatibility, bilingual README, changelog, source metadata, generated source, CT source and release notes consistent with the shipped public version and its local adaptation.
- Preserve relevant regression coverage. Build Debug and optimized x64 Release. Beta 5.3.2 requires 134 regression tests, the frozen 41-test portable menu suite, and 18 cold-start tests with 19,892 synthetic CPU frames, 852 relocated payload comparisons and 840 unchanged other-hook comparisons. The frozen suite retains: 4,280 byte comparisons, 15,880 synthetic CPU comparisons and 12 ASLR layouts. Run 28 C# self-checks, 852 current-profile comparisons and 3,780 complete prior-profile comparisons across 60 layouts for each build; record actual results rather than treating requirements as completed evidence. Verify the original 60 templates/fixups, 720 payloads and 720 patches against the immutable Beta 5.2 baseline. Check exact constructor capture, epoch-zero construction followed by native epoch-one completion, current-generation camera ownership, copied timing-hash contents and identity rechecks, once-only aura queueing, same-address reload, stale/foreign selections, lock/generation interleavings, native fallback, memory-MOVSS upper-lane semantics and ABI preservation. Retain prior element, Salt, ladder and interaction coverage. Recognize supported prior 55/59/60/70/71-hook installations read-only and require restart rather than migrating their allocations. Check newly installed executable code and seven writable, non-executable data pages. Include complete native function instruction-pointer and saved-return exclusions for menu installation dependencies, including the complete BaseMode aura frame. Distinguish public portable tests with synthetic records and explicit native-call stubs, private native-input regressions and user gameplay. Historical frozen checks are not newly rerun checks.
- Publish only selected tool/source/documentation files. Do not publish credentials, personal paths, raw private logs, game resources, historical third-party CT archives, dependency binaries or memory/code dumps.
- Export the complete source ZIP from exact Git-tracked blobs. Refuse private directories and binary artifacts, verify every source file against the reviewed commit, and include build instructions and pinned development requirements.
- The current owner-requested Release attachment inventory is exactly **the Windows x64 EXE and the source ZIP**. Store source-linked checksums, verification, component inventory and build provenance inside source ZIP build-info/ and/or the Release body. Retain CI attestations with GitHub and link them in the body; do not upload extra Release attachments.
- Check the exact game image and native signatures at runtime, decline unrecognized modifications and keep repeated enable idempotent.
- Prepare a Draft and immutable annotated tag, inspect exact source/tag/assets before publishing as Pre-release, then download and verify again. Never move an existing tag. Published assets are retained except for the explicitly authorized Beta 5.1 replacement below; that replacement requires validation of the new assets before removing the old ones.
- Verify actual owner/authorized publisher identities, remote source commit/tree, annotated tag, notes, exact two-asset names/counts/sizes/SHA-256 and complete source ZIP contents. The published release and asset IDs must match the inspected draft.
- Before tag creation and immediately before publication, require the same clean source commit and unchanged remote main. The owner explicitly requested publishing **Beta 5.3.2**. The version-scoped push-triggered Actions flow may publish this one reviewed `1.0.0-beta.5.3.2` release only after exact version/source/Draft/asset verification; require menu preview revision 2, eleven menu hooks, aura revision 1, camera reload revision 1 and accepted distance 740/height −45, cold-start revision 1 and bounded waits of 1800 asset frames / 7200 total frames. Future versions remain Draft-only without their own authorization. Do not reuse the historical version/Release-ID-scoped `.github/workflows/hotfix.yml` replacement. Record the exact source commit/tree, actor identities and final remote readback. The previous Beta 5.3 and Beta 5.2 publication authorizations remain historical.

## Historical authorized Beta 5.1 Hotfix replacement

The owner explicitly requested replacing the prior Beta 5.1 release with a Hotfix. Reuse existing Release ID **407938999**, change its tag/title/body to **v1.0.0-beta.5.1.hotfix.1 / 1.0.0 Beta 5.1 Hotfix 1**, and replace its two attachments. Validate the newly built EXE and complete source ZIP against the exact reviewed source commit/tree, including downloaded sizes/hashes and source contents, before removing the superseded Beta 5.1 attachments. Then verify the final release record, exact two-asset inventory, Pre-release=true and latest=false.

Use the specifically authorized `.github/workflows/hotfix.yml` Actions workflow, restricted to **1.0.0-beta.5.1.hotfix.1** and Release ID **407938999**. Keep the old **v1.0.0-beta.5.1** annotated-tag object **4590de9c41d5954541b5f34e6a05476a9eb6a4d2** unchanged and bind the new Hotfix tag to the exact reviewed source commit. Validate the new assets before deleting only the two superseded Beta 5.1 attachments. Retain historical committed release notes/validation/source and other releases. Record Actions publisher/uploader identity and final readback. This workflow authorization is limited to this replacement; it is not a general automatic replacement policy. Any staging Draft is a verification artifact and must not leave an extra public Hotfix release record.

## Beta-specific scope and deferred items

- This is a portable Windows Beta, not an APK or installer. Android installation/certificate gates are inapplicable.
- No Windows Authenticode signer is configured. Do not describe a Beta as signed; protected signing is a future Stable requirement.
- Local game tests apply only to the recorded Steam build and tested flows. Public packaging does not establish new cold-injection, full mission-transition, save/load or multi-PC coverage.
- Beta 5.3.2's cold-start test EXE was user-confirmed after a full game-process restart and a direct map/base status-page visit before entering any mission. Model, idle, framing and mist were normal. Read-only evidence recorded 498 native-gate wait frames, 34 asset-wait frames, one preload, no fallback and 45 stable-ready samples. Its 71 hooks/native targets must equal the final public source payloads. Local Debug/Release results and hashes belong in docs/validation-beta5.3.2.json; the CI-built binary is a separate build and its download verification must be recorded separately. Do not claim the final CI EXE itself was gameplay-tested.
- Beta 5.3.1's private live revision was user-confirmed for native preview mist, camera distance 740/height −45, idle and absence of William overlays after page reopen and main-menu reload. The final standalone EXE's first enable/reload in a fresh process remains untested. The local snapshot passed 134 regressions, 41 menu tests, and 28 C# self-checks / 852 current-profile / 2,928 prior-profile comparisons for both Debug and Release. Those local records retain their original build identity in docs/validation-beta5.3.1.json; final CI-built/downloaded hashes and source commit/tree belong in the release ZIP build-info/ and body. Do not label local checks or local EXE hashes as CI results.
- Beta 5.3's temporary in-game preview revisions were user-confirmed for Hino-Enma's model/skeleton, native idle, removal of William body/armor overlays and camera distance 740/height −45. Coverage is the equipment/status preview opened from the mission-selection map or base. Do not claim every in-mission menu or aspect ratio. Final-public-EXE first enable/reload in a fresh process remains untested.
- Final public-source offline checks passed 133 regressions, 25 menu tests, and 28 C# self-checks / 840 current-profile / 2,088 prior-profile comparisons for both Debug and Release. Source/CT checks passed for 70 hooks, 636 unique labels and 840 namespace comparisons. The public build adds complete menu installation-safety dependency guards; docs/validation-beta5.3.json records its actual reports and local public-source EXE hashes. Final CI-built/downloaded hashes are recorded separately. Unchanged hook payloads do not imply unchanged EXE bytes or new gameplay confirmation.
- Beta 5.2's innate element result covers the user's Raikiri “Imbue Lightning +8” with J, I, body charge, needles and life drain in the second five-hook temporary revision. The local revision-2 EXE's 23 self-checks/720 comparisons and private regression's 20 tests/959 CPU comparisons are distinct from the public 26-check build and its actual recorded portable CPU results. The final public EXE has not been gameplay-tested for fresh-process first enable. Do not claim every element, weapon affix, move variant or quantified final damage/status strength.
- Completed public Debug and Release each passed the 26 self-checks, 720 current-profile comparisons and 1,368 prior-profile comparisons. Source/CT verification passed 60 hooks, 555 unique local labels, 720 namespace comparisons and six negative guards. See docs/validation-beta5.2.json for final portable CPU results and source/build hashes; these completed offline checks do not constitute live game validation.
- The selected permanent element follows valid temporary talisman/Living Weapon priority. Needle paralysis and the roar's effects remain protected; the roar is excluded from added elements. Ordinary body attacks use native primary enchantment priority, without promising an independently stacked body paralysis channel. An elemental-damage percentage alone is not an innate enchantment.
- The accepted ladder second revision was user-confirmed for up/down climbing, per-step movement and exit height, with two ladder objects observed read-only. All ladders and enemy interruptions remain unverified. Its earlier local EXE's 22 checks and private integrated 50 tests/693 CPU comparisons were distinct from the historical public Hotfix 1 build's 23 checks/708 comparisons; they are not Beta 5.2 build results. Final public cold first-enable remains untested.
- Beta 5.1's post-defeat visual grab is scoped to the reported Nouhime / Yuki-Onna with loaded compatible resources. The temporary revision's two consecutive user-confirmed grabs and defeated-pose restoration must be distinguished from the final production build and dynamic-binding/reload verification. A zero-HP target receives no additional damage or healing; no revival or direct mission/save-state write is added. Do not claim all defeated Bosses or corpses are supported.
- Beta 5's seven reported new special-item effects and current Salt use/interruption result are user-confirmed. Salt's additional Common 205/85 routes have local CPU coverage only and remain unobserved in gameplay. Do not claim complete Salt interruption/enemy coverage.
- Document compatible shortcut items at slot 2 on the **first** item shortcut bar. Other shortcut positions retain Boss moves. Some non-critical item use remains unfixed.
- Immutable-release enforcement depends on repository configuration. If unavailable, retain tagged source, recorded hashes/provenance and the prohibition on replacing published assets outside this specifically authorized Beta 5.1 replacement.
- CI attestation covers the exact CI-built EXE and source ZIP only. It does not attest a separately built local EXE, certify gameplay correctness or replace code signing.
- Checks of an attestation statement, source and subjects are distinct from independent cryptographic verification.

## Change control

Keep fixes scoped, record known defects, preserve Boss base-plus-bonus calculation, and do not add undocumented dependency upgrades or silently broaden compatibility. RC/Stable requires renewed gameplay and broader compatibility review before release. User instructions govern selected release scope; this two-attachment policy supersedes the historical Beta 1–3 attachment inventory.
