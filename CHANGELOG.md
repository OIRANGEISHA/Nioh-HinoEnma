# Changelog

## [Unreleased]

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

[Unreleased]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/compare/v1.0.0-beta.2...HEAD
[1.0.0-beta.2]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.2
[1.0.0-beta.1]: https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.1
