# Changelog

## [Unreleased]

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

[Unreleased]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/compare/v1.0.0-beta.5.1...HEAD
[1.0.0-beta.5.1]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.5.1
[1.0.0-beta.5]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.5
[1.0.0-beta.4.1]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.4.1
[1.0.0-beta.4]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.4
[1.0.0-beta.3]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.3
[1.0.0-beta.2]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.2
[1.0.0-beta.1]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.1
