# Changelog

## [Unreleased]

- Stabilize source-only Windows verification by expressing the project's decimal Intel literals with an explicit radix before invoking Keystone 0.9.2. Keep the Beta 5.3.2 hook source, generated C#, CT, runtime payloads, release tag and published assets unchanged. Add seven numeric parsing regressions and preserve the frozen 41-test menu suites byte-for-byte.
- 修正 Windows 源码验证中 Keystone 0.9.2 默认数字进制不稳定的问题；汇编前显式标注数字进制，游戏补丁、已发布标签和附件不变。新增七项数字解析回归，原有 41 项菜单测试文件保持原样。

## [1.0.0-beta.5.4.2] - 2026-10-11

- 修复九尾妖狐倒地后重攻击仍为旋转的问题，按当前所属资源绑定原生 `4026/1210 → 1273/1211` 玩家链与 `1274/31010` 目标链。
- 补齐主辅动画与主辅事件，保留合法晚期调度及目标第 510 帧 local77 原生死亡事件；在已验证的起手、待配对区间保护 query86，生命及任务状态由游戏处理。
- 保持 81 处入口，八处共享载荷增加双 Boss 路由且完整保留原有大蛇处理体，其余 73 处逐字节一致。九尾使用独立 512 字节动态绑定，分配扩大到 0x51000；旧 Beta 5.4.1 增加为完整只读重启身份。
- 启动工具支持分块核对较大的正式重攻击载荷。事件表 DWORD 边界溢出和遗留九尾阶段遮蔽大蛇路由均补齐拒绝／回退检查。
- 203 项源码回归、四项来源证明及 Debug/Release 核对全部通过；每个 EXE 有 29 项自检、972 次当前和 6564 次历史载荷比较。场景候选与精确新 EXE 的完整重启复测均完成击杀、剧情继续和控制恢复；正式版只读核对限于原生结束状态，其范围和哈希单独记录在 docs/validation-beta5.4.2.json。
- 用户反馈的无间狱坐船闪退尚未修复，按要求列入已知问题，后续单独处理。
- 用户反馈的无间狱无法前往下一层、交互进度满后没有反应尚未修复，按要求列入已知问题，后续单独处理。
- 用户于 2026-10-11 授权源码及记录推送到 GitHub，并发布本版独立 Pre-release；发布前核对完整源码、四项来源证明和下载附件。历史发布与原本地交付保留原始身份；Beta 5.4.2 未重打大蛇整场。

## [1.0.0-beta.5.4.1] - 2026-10-11

- 修正 Beta 5.4 完整重启后八岐大蛇最后处决仍触发旋转攻击的资源绑定错误：分别保存飞缘魔当前待机与原生 common 待机，重攻击过渡从后者查找，入口和结束恢复继续使用飞缘魔待机。
- 在处决3491起手尚未完成配对的区间，防止满槽九十九query86提前分派169打断；保留原生false尾声和ABI，其余状态沿原路径。
- 核定并精确匹配八只蛇头的template/placement身份，补齐原生就绪3204；元数据按真实DWORD结构允许4字节对齐，并验证模板一致。
- 默认CPU模型分离两种待机所有者，并覆盖八头身份、元数据、待配对间隙、资源所有权与异常回退。完整布局81处，保留Beta5.3.2的71处载荷；旧Beta5.4作为精确只读重启身份。
- 本次修订实机结果、构建哈希与本地源码包另行记录；九尾妖狐仍需独立取证。

## [1.0.0-beta.5.4] - 2026-10-11

### Fixed

- Add nine scoped Yamata-no-Orochi execution hooks and dynamic resource discovery while preserving all 71 Beta 5.3.2 payloads. Supply matching native action, motion and auxiliary event resource views without direct HP, mission or save writes.
- Guard zero-length and non-finite ray queries through the native no-hit epilogue, including the post-kill interval after both pairing references are cleared.
- 修复八岐大蛇处决的辅助事件资源缺失与几何查询卡住；保留原生伤害、击杀事件、结束动作及控制恢复。

### Validation and package scope

- Scene-bound candidate v5 passed 35 offline tests; numerical guard v2 passed 13 offline tests. The user confirmed the post-kill sequence and restored control, with phase 0, recovered idle 1, head HP 0 and native head-death count 8. These trials have a separate identity from the new dynamic-binding EXE.
- Prepare a local package only. New integration proofs and exact Debug/Release EXE checks must pass before packaging; the final EXE has not been gameplay-tested. Preserve historical tags, published assets and validation records.
- Local checks passed 166 complete source regressions, 23 execution tests (included in that total), and the frozen 59 menu/cold-start tests. Debug and Release each passed 29 self-checks, 960 current payload comparisons across 12 layouts and 4632 prior payload comparisons across 72 layouts. Preserve all previous71 payloads and patches (852 comparisons each) and the immutable Beta 5.2 basis.
- Nine Tails execution remains an independent investigation. Its native chain, resources, kill events, terminal recovery and exit geometry require separate evidence; Orochi IDs and counters do not establish compatibility.
- Record the failed auxiliary-event lookup, native paired execution chain, zero-vector/NaN freezes before and after kill, correct late query epilogue and Nine Tails investigation path in `docs/debugging/orochi-execution-2026-10-11.md`.

## [1.0.0-beta.5.3.2] - 2026-10-11

### Fixed

- Fix the first mission-map/base equipment/status preview reverting to William after a complete game restart. Wait for both native map-loading gates before consuming the asset timeout and retry temporarily absent resource managers within the same bounded generation, without duplicate preload requests.
- Change only the readiness payload among the existing 71 hooks. Keep the other 70 payloads, native idle, preview mist and accepted camera distance 740/height −45. Recognize complete Beta 5.3.1 installations read-only and require restart.

### Validation and release scope

- The cold-start test EXE passed a full game-process restart and direct status-page visit before entering a mission; the user confirmed model, idle, framing and mist. Observed one preload, 498 gate-wait frames, 34 asset-wait frames and no fallback. The final public EXE is a separate build verified against the same hook payloads.
- Pass 134 source regressions, the frozen 41-test menu suites, and 18 cold-start tests with 19,892 synthetic CPU frames. Both builds pass 28 C# checks, 852 current-profile and 3,780 previous-profile comparisons; preserve the immutable 60-hook Beta 5.2 basis. Local and CI results remain distinct.
- Owner-authorized new immutable Pre-release, exactly the EXE and Git-source ZIP; preserve historical releases. Compatible items use slot 2 on the first shortcut bar. Some non-critical item use remains unfixed.

## [1.0.0-beta.5.3.1] - 2026-10-10

### Fixed

- Restore Hino-Enma's surrounding native Yokai Realm mist in the mission-map/base equipment and status preview. Verify the independently allocated timing hash array's complete contents and queue the owned aura once per completed display generation.
- Keep the accepted camera distance 740 and height −45 after reopening the status page or continuing from the main menu. Preserve the eight display/appearance hooks and 60-hook gameplay basis, replace two camera hooks and add one aura hook, for 71 hooks.

### Validation and release scope

- The private live revision was user-confirmed for mist, framing, idle and no William overlays after page reopen and title reload. The packaged EXE's first enable/reload in a fresh game process remains untested.
- The local source passed 134 regressions and 41 portable menu tests: 4,280 byte comparisons, 15,880 synthetic CPU comparisons and 12 ASLR layouts. Debug and Release each passed 28 C# self-checks, 852 current-profile and 2,928 prior-profile comparisons; the original 60-hook basis passed 720 payload and patch comparisons. Keep these local results distinct from final CI build and download verification.
- Prepare the owner-authorized new immutable `v1.0.0-beta.5.3.1` Pre-release with exactly the Windows x64 EXE and complete Git-source ZIP. Publish only after source, tag and downloaded-asset verification; earlier releases remain unchanged. Unsigned, latest=false.
- Some non-critical item use remains unfixed. Compatible shortcut items stay in slot 2 on the first bar; existing gameplay controls and limitations remain.

## [1.0.0-beta.5.3] - 2026-10-10

### Added

- Show Hino-Enma's model, skeleton and native idle in the equipment/status preview opened from the mission-selection map or base. Suppress William's body and armor overlays for the owned map display actor while retaining native stats and equipment bonuses.
- Adjust the owned preview's computed camera distance to 740 and target height to −45 for full-body framing. Bind this to the newly constructed instance and invalidate it on map reload; William, gameplay and foreign instances keep native fallback.
- Add ten scoped preview hooks to the unchanged 60-hook Beta 5.2 basis, for 70 hooks. Keep the existing controls, innate weapon elements and Boss base-plus-growth/equipment calculation.

### Validation and release scope

- The temporary in-game revisions were user-confirmed for the model, native idle, removal of William overlays and accepted framing. The final public EXE's first enable/reload in a fresh game process remains untested. Coverage is the reported map/base preview, not every in-mission menu or screen ratio.
- The final public source passed 133 regression tests (121 retained plus 12 release-evidence refusal checks) and 25 portable menu tests: 2,490 byte comparisons, 10,005 synthetic CPU comparisons and 12 ASLR layouts. Public-source Debug and Release each passed 28 C# self-checks, 840 current-profile comparisons and 2,088 complete prior-profile comparisons. Source/CT checks passed for 70 hooks, 636 unique labels and 840 namespace comparisons; the unchanged 60-hook basis passed 720 payload and 720 patch comparisons. Actual results are recorded in docs/validation-beta5.3.json; exact Git-source provenance and final CI asset hashes are recorded when packaged/published.
- Preserve historical release records and the immutable Beta 5.2 baseline. Some non-critical item use remains unfixed. Compatible shortcut items stay in slot 2 on the first bar; digit 5 is roar, F6 purification and digit 9 native Living Weapon/guardian attack.
- Publish a new immutable `v1.0.0-beta.5.3` Pre-release with exactly the Windows x64 EXE and complete Git-source ZIP. Earlier tags/assets remain unchanged. Unsigned, latest=false.

## [1.0.0-beta.5.2] - 2026-10-10

### Fixed

- Pass the selected melee weapon's native innate fire, water, lightning, wind or earth element to supported Hino-Enma kicks, umbrella attacks, body charge, needles and life drain. Temporary elemental talismans and Living Weapon retain priority. Re-equip the selected weapon or reload the character for native refresh.
- Preserve needle paralysis and the roar's original effects; exclude the roar from added elements. Ordinary body attacks follow the native primary enchantment priority, without claiming a second independent paralysis channel.
- Update four existing hooks and add one, for 60 hooks. Preserve all 55 unrelated Hotfix 1 hooks, Boss base-plus-growth/equipment calculation and existing controls.
- Extend launcher recognition to the complete supported older 55/59-hook installations. Verify full entry sites and payloads read-only and reject damaged or unknown configurations. New installation checks cover executable code and three writable, non-executable data pages; this does not claim a VirtualQuery check of old live page protection.

### Validation and release scope

- The second temporary revision was user-confirmed with Raikiri's “Imbue Lightning +8”: J, I, body charge, needles and life drain all showed lightning and gameplay remained normal. The five-hook live trial is separate from the final public EXE; fresh-process first enable, exact damage/status strength and every innate element remain unverified.
- The local second-revision EXE passed 23 self-checks and 720 payload comparisons, and its private native-code regression passed 20 tests and 959 CPU comparisons. Those are local results. The public Beta 5.2 integration adds launcher checks; its actual Debug/Release and portable CPU results are recorded in the Beta 5.2 validation file.
- Public Debug and Release each passed 26 self-checks, 720 current-profile comparisons and 1,368 complete prior-profile comparisons (55/59 hooks × 12 layouts). Source/CT checks passed for 60 hooks, 555 unique local labels, 720 namespace comparisons and six negative guards. These checks do not access the game or establish fresh-process first enable.
- Retain the ladder and defeated Nouhime / Yuki-Onna compatibility, previous item/interaction fixes and additive stat calculation. Some non-critical item use remains unfixed; compatible shortcuts remain in slot 2 on the first bar, with other skill/move bindings unchanged.
- Publish a new immutable `v1.0.0-beta.5.2` tag and Pre-release with exactly the Windows x64 EXE and complete source ZIP. Earlier tags, assets and historical records remain unchanged. Unsigned, latest=false.

## [1.0.0-beta.5.1.hotfix.1] - 2026-10-09

### Fixed

- Fix the reported underground-to-surface ladder in the Mount Hiei mission: falling before the exit, per-step teleporting and excessive exit height came from Hino-Enma's 1.8-scale displacement being sampled for a pending ladder clip before the current action changed.
- Normalize both current and pending owned Common-ladder clip samples, current-frame displacement and the matching rendered layer. Preserve the actor's normal model scale and all 55 Beta 5.1 hooks; add four scoped hooks for a total of 59.

### Validation and release scope

- The second temporary revision was user-confirmed for up/down climbing, per-step motion and exit height. Read-only observation recorded two ladder objects and their transitions. All ladders, enemy interruptions and final-public-EXE cold first-enable remain unverified; portable build and private local checks are recorded separately in the Hotfix validation.
- Retain Beta 5.1's post-defeat grab, keyboard bindings and limitations. Compatible shortcut items remain in slot 2 on the first bar; some non-critical item use remains unfixed.
- The owner explicitly requested replacing the Beta 5.1 release with this Hotfix. The publication plan reuses its release record with a new immutable Hotfix tag, verifies the new EXE/source ZIP before removing the superseded two attachments, and retains the old Beta 5.1 tag and historical records; the owner separately authorized the version/Release-ID-scoped `.github/workflows/hotfix.yml` Actions workflow, with identities and final readback recorded at publication. Other releases remain unchanged and other versions remain Draft-only without separate authorization. Unsigned Pre-release, latest=false.

## [1.0.0-beta.5.1] - 2026-10-09

### Added

- Complete visual life-drain pairing for the reported defeated Nouhime / Yuki-Onna while she remains loaded with the required reaction resources. Use the existing digit 1 binding.
- Bind the current source/target instances with ownership, distance, defeated-state and resource checks, refreshing bindings after character recreation.
- Suppress additional damage and healing against the zero-HP target and restore the original defeated pose after pairing. No revival or direct mission/save-state write is added.

### Validation and limits

- The temporary revision was user-confirmed through two consecutive complete grabs, defeated-pose restoration and normal movement/menus. Production build, portable/offline checks and gameplay evidence are recorded separately in the Beta 5.1 validation record; earlier evidence remains historical.
- This feature does not establish support for all defeated Bosses or corpses. Retain Beta 5's features, keyboard bindings and known limitations, including some non-critical item use remaining unfixed.
- Release attachments remain exactly the Windows x64 EXE and complete source ZIP, with CT source inside the ZIP. Earlier tags/assets/records remain unchanged. Unsigned Pre-release.

## [1.0.0-beta.5] - 2026-10-09

### Added

- Fifth public Beta based on local 0.58, retaining Beta 4.1 and earlier public behavior.
- Reported Guardian Spirit Talisman, Hyottoko Mask, Conch, Yokai Water Pot, Kodama Bowl, Himorogi Branch and Summoner's Candle use; the seven reported item effects are user-confirmed.
- Correct shortcut documentation to slot 2 on the **first** item shortcut bar. Other shortcut positions retain Hino-Enma skill/move bindings; compatible items can also be used from the bag.

### Fixed

- Read longer installed payloads in bounded chunks, preserving full-length/address checks and partial-read refusal.
- Restore Salt consumption, throwing effects and the reported Yokai ki hit. Scope recovery to the current player's owned Salt action and supported interruption resources while preserving native effects and fallback behavior.
- The latest reported Salt use/interruption test completed normally with movement and attacks restored. Additional Common 205/85 interruption routes have CPU-only coverage and are not gameplay-confirmed.

### Validation and limits

- Local 0.58 passed 23 new native-CPU regression checks using private verified native-code inputs. A separate 23 public CPU checks passed (8 retained door-instance, 5 new special-item and 10 new Salt checks), using synthetic records and explicit Win64 stubs. They do not run the native damage/event engine or inventory commit. Public checks, local native-code checks and user gameplay have distinct scope; historical proofs remain frozen.
- Debug and Release each passed 21 EXE self-checks and 600 payload comparisons (50 hooks × 12 layouts), with final results recorded in the Beta 5 validation record. These checks do not access the game or establish final-EXE cold first-enable.
- Some non-critical item use remains unfixed; all Salt interruptions, item effects, affixes, interactions and mission transitions are not verified.
- Release attachments remain exactly the Windows x64 EXE and complete source ZIP. Earlier tags/assets/records remain unchanged. Unsigned Pre-release.

## [1.0.0-beta.4.1] - 2026-10-09

### Fixed

- Fix the reported latched door in the Shigisan spider mission. Replace the fixed-instance check with the native latched-door type check. The user confirmed that the reported door opens; existing request, ownership and resource guards remain.

### Validation and limits

- Based on local 0.51. Eight new native-CPU regression checks, 19 EXE self-checks and 588 EXE/source payload comparisons passed (49 patches × 12 layouts). Earlier regression evidence remains frozen; this does not claim a rerun of all historical checks.
- Retain Beta 4's features and keyboard bindings. Some non-critical item use remains unfixed; not every map, door variant or interaction is verified.
- Publish only the Windows x64 EXE and complete source ZIP. Beta 4 and earlier tags/assets/records remain unchanged. Unsigned Pre-release; public cold first-enable remains unverified.

## [1.0.0-beta.4] - 2026-10-09

### Added

- Fourth public Beta based on local 0.50, incorporating local 0.45–0.50 after Beta 3. Earlier tags/assets/historical records remain unchanged.
- Publish only the standalone Windows x64 EXE and source archive as release attachments. The source archive includes usage and keyboard documentation; GitHub's automatic source downloads remain available.
- Document the tester’s current bindings: W/A/S/D movement, J kick, I umbrella, K evade, Shift ki recovery, Q + Space flight, Alt flight charge/dive, digit 1 life drain, digit 5 ground/air roar, F6 purification and digit 9 native Living Weapon/guardian attack. Digits 1–4 conflict with shortcut items; compatible items must be used from the bag.

### Fixed

- Restore the accepted fallen-NPC rescue request’s native action entry. The user confirmed that the reported Ginchiyo can be revived and movement/J/I/digit 5 work afterward; native rescue animation, NPC recovery and interaction exit remain under the game’s control.
- Retain local 0.49 NPC dialogue compatibility. The reported small Yokai gesture prompt can continue after selecting “交给我吧” and performing it once.
- Retain local 0.48 latched-door interaction, local 0.47 enemy Hino-Enma death cleanup, Signpost Talisman compatibility and earlier public-action fixes.

### Validation and limits

- Local 0.50 passed 8 new offline regression checks. The EXE passed 19 self-checks and 588 EXE/source payload comparisons (49 patches × 12 address layouts), without game access. Earlier research proof remains frozen; this is not a rerun of every historical check.
- Ginchiyo rescue and restored post-rescue movement/J/I/digit 5 are separately user-confirmed. Other NPCs and repeated rescues of the same NPC remain unverified.
- Some non-critical item use remains unfixed. Reported item compatibility does not establish support for every recovery/buff or ninjutsu item; shortcut-item conflicts remain.
- Hino-Enma’s displayed gesture can still remain laughter; the full set of gesture animations is not adapted. Additional roar elements, other guardians, native shooting, actual Boss weapon switching, full affix/interaction/transition coverage and final-public-EXE cold first-enable remain outside confirmed scope. Unsigned Beta.

## [1.0.0-beta.3] - 2026-10-08

### Added

- Third public Beta based on local 0.44, incorporating local 0.36–0.44 after Beta 2. Earlier tags/assets/historical records remain unchanged.
- Native Boss HP/ki/attack/defense curves map level 1/index 1 to level 400/index 1410 linearly, rounding down. Valid saved levels 1–750 are read, mapped levels above 400 are capped; higher scene indices and additive native growth/equipment bonuses remain.

### Fixed

- Native hot-spring sit/wait/stand/exit. Current-pool animation, Buff and restored movement/J/I are confirmed; same-version William also automatically stands after a short wait.
- Reported bag Lightning/Fire Talismans and Travel Amulet, including repeated talisman eligibility.
- Elemental needle/life-drain paths. The user confirmed needles, body charge and life drain during Living Weapon; the roar’s intrinsic status and auxiliary effects remain preserved. An additional roar element is excluded.
- Native guardian recovery: Kato shrine recall and death-grave pickup, followed by digit-9 startup/attacks, are confirmed.

### Validation and limits

- Preserve earlier interaction/ladder/dojo/grab/Living Weapon behavior within recorded scope. Local research: 499 prior checks frozen plus 8 new hot-spring checks, not 507 rerun checks.
- New public Debug/Release each passed 19 C# checks and 540 comparisons (45 hooks × 12 layouts), without game access. Pure-source/CT checks and offscreen UI review passed.
- Current-pool comparison does not prove exact durations or the older Hino exit branch. Other pools/guardians, needle paralysis strength, damage/healing, actual level spending and new growth save/load remain pending.
- Signpost marking is unresolved; roar plus an added element is excluded. Public cold first-enable, direct CT enable, full item/affix/transition coverage, final icon, native shooting and actual Boss weapon switching remain outside confirmed scope. Unsigned Beta.

## [1.0.0-beta.2] - 2026-10-08

### Added

- Second public Beta, based on local 0.35. Beta 1 remains unchanged.
- Select William or Hino-Enma for the next mission load.
- Digit 5 for ground/air roar and F6 for independent Yokai Realm purification.
- Digit 9 for native Living Weapon reinforcement and guardian combat summons, with repeat requests after retirement, including the tested infinite-Living-Weapon case.
- Dojo compatibility for the reported locks, ki pulse, purification, melee/ranged weapon-switch and Living Weapon steps. Shooting practice continues after defeating its target.

### Fixed

- Native ladder entry, ascent, descent and exit; climbing no longer dispatches Hino-Enma's roar. Both directions and post-exit movement/J/I/digit 5 are confirmed.
- Complete life-drain grabs on the reported Yoki, Dwellers and Onryoki, retaining the grab animation instead of a damage/healing substitute.
- Reported bag Ninja's Locks and Small Spirit Stone use, while retaining native item effects and consumption. Existing self-recovery/buff compatibility remains.
- Digit 9 could refuse full-charge Living Weapon startup when a 64-bit resource-ID read included adjacent padding. Read the native 32-bit resource ID; offline regression passed, and the user confirmed corrected startup, guardian attack and repeat summons after retirement.

### Validation and limits

- Preserve Boss base values plus growth/equipment bonuses and the previously confirmed interaction fixes.
- Local research: 413 Python checks. Portable verification: 19 C# checks and 480 native-payload comparisons across 40 hooks and 12 layouts.
- All enemies, guardians, ladders, item effects, affixes and transitions are not individually verified. Native shooting, actual Boss weapon switching and shortcut-item conflicts remain open.
- Actual guardian hit-damage values, full Living Weapon protection and final public EXE cold first-enable remain unverified. The Windows Beta is unsigned.

## [1.0.0-beta.1] - 2026-10-07

### Added

- First public Windows x64 Beta: standalone Hino-Enma launcher, source and guarded CT for the verified Steam Nioh Complete Edition build.
- Native player growth, armor defense and selected melee-weapon attack increments added to the Boss baseline while retaining Hino-Enma's model and moveset.
- Bilingual usage documentation, known-limitations record, source build and release checksums.

### Fixed

- The locally reported chest, key-door, prison-door and one-sided-door interaction failures; corpse loot remains available.
- Flight camera pulling down; Himorogi Fragment mission return from the bag; Kodama guide-home; classified self-consumables, with Sacred Water confirmed.
- The reported blood tomb failing after its progress bar completed; the user confirmed revenant summoning after the fix.
- Native weapon HUD refresh paths reading incompatible gear; final visual icon confirmation remains pending.

### Known limitations

- Non-humanoid Boss life-drain grabs, shortcut conflicts, complete interaction coverage, individual item/affix effects and cold first-enable verification of the final public EXE remain open.

[Unreleased]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/compare/v1.0.0-beta.5.3.1...HEAD
[1.0.0-beta.5.3.1]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.5.3.1
[1.0.0-beta.5.3]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.5.3
[1.0.0-beta.5.2]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.5.2
[1.0.0-beta.5.1.hotfix.1]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.5.1.hotfix.1
[1.0.0-beta.5.1]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.5.1
[1.0.0-beta.5]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.5
[1.0.0-beta.4.1]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.4.1
[1.0.0-beta.4]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.4
[1.0.0-beta.3]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.3
[1.0.0-beta.2]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.2
[1.0.0-beta.1]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.1
