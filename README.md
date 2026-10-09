# Nioh Hino-Enma

[简体中文](README.zh-CN.md)

**Current version: 1.0.0 Beta 5.2 / Pre-release.**

A standalone Windows tool that replaces the playable character in **Nioh: Complete Edition** with Hino-Enma while preserving her model and moveset. Beta 5.2 passes the selected melee weapon's innate element to her supported attacks. Raikiri's “Imbue Lightning +8” is user-confirmed on kicks, umbrella attacks, body charge, needles and life drain. Earlier ladder, defeated Nouhime / Yuki-Onna grab, item and interaction fixes are retained. Player growth, armor and selected-weapon bonuses remain additive to the Boss baseline.

## Download and use

Get the Windows x64 EXE or source archive from [Beta 5.2](https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.5.2). The release attachments are only `Nioh-HinoEnma-1.0.0-beta.5.2-windows-x64.exe` and `Nioh-HinoEnma-1.0.0-beta.5.2-source.zip`; the source archive includes instructions and keyboard documentation. GitHub also provides its automatic source ZIP/tar downloads. You do not need Cheat Engine, Python or the source archive to use the EXE.

1. Start the Steam game normally and stop at **NEW GAME / CONTINUE**.
2. Run the tool. After it reports that the next character will be Hino-Enma, load a mission.
3. The newly created player becomes Hino-Enma. You can close the tool.
4. To switch to William or Hino-Enma, select that character in the tool, return to the main menu and load the mission again. Run the tool again after restarting the game.

Repeated runs recognize the existing installation and retain the character choice for that game process. A new game process defaults to Hino-Enma after enabling. The tool checks the exact executable and instruction signatures; an unsupported build is refused. If access fails, try running the tool as administrator. To return to an older public version, exit Nioh first and use the unchanged [Beta 1 release](https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.1).

## Compatibility

- Windows x64 with .NET Framework 4.x and the **Steam Complete Edition 1.24.8** build, shown as **1.24.08** in the game window.
- Exact supported executable SHA-256: `0c3508c6b4d0696d84423949df9faccb3f9c6d93833854e1e17a78d66defc389`.
- Epic and other executable builds have not been adapted. Matching a version label alone is insufficient.
- The EXE changes the current process; game installation files do not need replacement. Game saves continue through the game's normal behavior; complete save/load and mission-transition coverage remains unverified.

## New in Beta 5.2

- Pass the selected melee weapon's native innate fire, water, lightning, wind or earth element to supported kicks, umbrella attacks, body charge, needles and life-drain hits. Elemental talismans and Living Weapon retain priority over the permanent weapon element.
- The second temporary revision was user-confirmed with Raikiri's “Imbue Lightning +8”: all five reported attacks showed lightning and movement, attacks and life drain remained normal. Other innate elements, exact per-hit damage and every attack variant have not been individually tested.
- Needle paralysis and the roar's original effects are retained; the roar does not receive an added element. Ordinary body attacks use the game's native primary enchantment priority. This does not promise a second independent paralysis channel on those body attacks.
- “Imbue [element] +N” supplies an element. A “[element] damage +N%” affix enhances matching damage already being dealt; that percentage alone does not add an element.
- Preserve Boss base-plus-growth/equipment calculation and earlier functionality. Four existing hooks are updated and one is added, for 60 hooks. Re-equip the selected weapon and close the menu, or reload the character, to refresh its native element.
- Exit and restart Nioh before upgrading from an earlier tool, then enable Beta 5.2 at the main menu.

## Retained Beta 5.1 Hotfix 1 fixes

- Fix falling before the exit on the reported underground-to-surface Mount Hiei ladder, per-step teleporting and excessive exit height. The pending climbing clip had still been sampled at Hino-Enma's 1.8 motion scale before becoming the current action.
- Four scoped hooks normalize current and pending Common-ladder displacement samples and the matching rendered layer for the current player. Actor model scale and all 55 prior hooks are preserved; the complete profile has 59 hooks.
- The second temporary revision was user-confirmed for up/down motion and normal exit height. Read-only observation recorded two ladder objects and their transitions. This does not establish coverage of every ladder or interruption.
- Do not mix different tool versions in one game process.

## Retained Beta 5.1 additions

- Digit **1** can request the complete life-drain grab animation on a defeated Nouhime / Yuki-Onna who remains loaded with the required reaction resources. No new key is added.
- The temporary revision was user-tested with two consecutive complete grabs. After each, she returned to her original defeated pose; movement and menus remained normal.
- A defeated target receives no additional damage or healing from this visual pairing. The compatibility does not revive her or directly write mission/save state.
- The production path binds the current player and target instances and checks ownership, distance, defeated state and loaded resources. It refreshes its bindings with the current character rather than using a saved process address. Other defeated Bosses or corpses are not claimed to be supported.

## Retained Beta 5 fixes

- Restore the reported Guardian Spirit Talisman, Hyottoko Mask, Conch, Yokai Water Pot, Kodama Bowl, Himorogi Branch and Summoner's Candle. Their reported summon, placement or mission-return effects are user-confirmed; the candle was tested after death while the guardian was lost, followed by normal guardian attack.
- Restore Salt consumption, throwing effects and the reported Yokai ki hit. The latest reported Salt use and interruption test passed with normal movement and attacks. Other Salt interruption paths have offline checks and still require gameplay confirmation.
- Read longer installed payloads in bounded chunks, with complete-length and address checks; a partial read is refused.
- Correct the item-shortcut documentation: **place compatible items in slot 2 on the first item shortcut bar**. Other shortcut positions keep their Hino-Enma skills or moves.

## Retained Beta 4.1 fix

- Fix the latched door in the reported Shigisan spider mission. Replace the fixed-instance check with the native latched-door type check, retaining request, ownership and resource guards. The user confirmed that the reported door opens; other maps and door variants are not all verified.
- Retain Beta 4's features, keyboard bindings and item-use limitations.

## Retained Beta 4 fixes

- Restore the accepted rescue request’s native action entry for the reported fallen Ginchiyo. The game handles the rescue animation, NPC recovery and interaction exit. The user confirmed that Ginchiyo can be revived and movement, J/I and digit 5 work afterward. Other NPCs and repeated rescues remain unverified.
- Retain local 0.49 NPC dialogue compatibility. At the reported small Yokai gesture prompt, selecting “交给我吧” and performing it once is confirmed to allow progress. Hino-Enma’s displayed gesture can still remain laughter; the full set of gesture animations is not adapted.
- Retain local 0.48 latched-door interaction, local 0.47 enemy Hino-Enma death cleanup, Signpost Talisman compatibility and earlier public-action fixes.
- Document the current tested keyboard layout below. **Some non-critical item use remains unfixed**; item shortcuts currently support only slot 2 on the first item shortcut bar. Other shortcut slots trigger Hino-Enma skills or moves. Compatible items can also be used from the bag.

## Retained Beta 3 fixes

- Restore native hot-spring sit/wait/stand/exit. Current-pool animation, Buff and restored movement/J/I are confirmed. Same-version William also automatically stands after a short wait there; exact durations and all pools are not claimed.
- Reported bag Lightning/Fire Talismans and Travel Amulet, including repeated elemental-talisman use. The user confirmed Living Weapon elements on needles, body charge and life drain. Original roar status and auxiliary effects are preserved; a second added element for the roar is excluded.
- Native Kato guardian recovery through shrine recall and death-grave pickup, followed by digit-9 startup and attacks. Other guardians remain pending.
- Native Boss HP/ki/attack/defense curves use a linear mapping from level 1/index 1 to level 400/index 1410, rounding down. Valid saved levels 1–750 are read, mapped levels above 400 are capped, and higher native scene indices are retained. Native growth/equipment/selected-weapon bonuses remain additive. Re-equip armor and close the menu, or reload the character, for normal refresh; no saved levels/points/scene indices or current HP are directly edited. Repeated refresh recomputes base plus bonuses.

## Retained features and tested scope

- Visible Hino-Enma replacement and basic movement, kick, umbrella attack and evasion.
- Locally tested boxes, key doors, prison doors, a door opened from one side and corpse loot.
- Flight camera correction; Himorogi Fragment from the bag; Kodama guide-home; Sacred Water from the bag; the reported blood tomb now summons a revenant.
- Native growth and armor recalculation added to Boss HP, ki and defense. User confirmed changes after re-equipping armor.
- Selected melee-weapon attack increment is added to Boss attacks. A sole equipped weapon is selected even if the other slot is empty. Weapon HUD refresh compatibility is included.
- Complete life-drain grab animations are confirmed on the reported Yoki, Dwellers and Onryoki. Target/resource checks remain; this is not a claim of support for every enemy or Boss.
- Native ladder interaction, climbing up and down, and leaving the ladder are confirmed. Hino-Enma movement, J/I and digit 5 work after leaving; ladder movement no longer invokes her roar.
- F6 purifies nearby Yokai Realm pools. Digit 5 directly invokes the roar on the ground or in the air; Alt retains the flight/dive move.
- Bag item compatibility includes the reported Ninja's Locks, Small Spirit Stone and self-recovery/buff paths. Dojo compatibility covers the reported locks, ki pulse, purification, weapon-switch and Living Weapon steps; shooting practice continues after defeating its target.
- Digit 9 starts native Living Weapon at full charge while retaining Hino-Enma's moves. Native attribute reinforcement is confirmed. Guardian attacks and repeated summons, including use with the tester's infinite-Living-Weapon trainer, are confirmed; measured hit damage remains untested.
- Fix the reported digit 9 full-charge startup refusal by reading the native resource ID as a 32-bit value. The earlier 64-bit read included unrelated padding. Offline regression passed, and the user confirmed startup, guardian attack and repeat summons after retirement in the corrected version.

The following bindings use the tester’s current game keyboard settings; other settings may differ. Number keys refer to the main keyboard row.

| Key | Action |
| --- | --- |
| W / A / S / D | Move |
| J | Kick |
| I | Umbrella attack |
| K | Backstep / evade |
| Shift | Restore ki |
| Q + Space | Take flight |
| Alt | Flight charge / dive |
| 1 | Life drain; also request the supported defeated Nouhime / Yuki-Onna visual grab |
| 2 (first item shortcut bar) | Use shortcut items; currently the only supported item shortcut slot |
| 5 | Ground / airborne roar |
| F6 | Purify nearby Yokai Realm pools; holding triggers once, release and press again to repeat |
| 9 | At full guardian charge while idle on the ground, start native Living Weapon and summon a guardian attack |

During Living Weapon, after the guardian retires and Hino-Enma is idle on the ground again, release and press 9 to repeat the summon. Use the game’s interaction key to enter a ladder, W to climb up and S to climb down; her moves resume after leaving.

**Item shortcuts currently support only slot 2 on the first item shortcut bar.** The user confirmed that placing an item there allows normal use because this slot is not bound to a Hino-Enma skill or move. Other shortcut slots trigger Hino-Enma skills or moves and retain their current bindings. Compatible items can also be used by selecting “Use” in the bag.

Space handles the compatible dojo ki-pulse/purification steps. Dojo weapon-switch combinations are Space + 2/3 for melee and Space + 1/4 for ranged; T handles the reported Living Weapon teaching step while preserving its Boss attack.

## Known limitations

- The innate-element gameplay result covers Raikiri's lightning on the five reported attacks in the second temporary revision. It does not establish every element, weapon affix, airborne variant or exact damage/status strength. Temporary enchantments keep native priority; ordinary body attacks do not gain a separately guaranteed paralysis channel.
- The ladder fix is confirmed for the reported trial locations, with two ladder objects recorded. Enemy interruptions and every ladder variant remain untested. Final-public-EXE first enable in a fresh process has not yet been gameplay-tested; source/build checks are recorded separately.

- The retained post-defeat visual grab covers the reported Nouhime / Yuki-Onna with loaded compatible resources. The two consecutive gameplay confirmations used a temporary revision; its separate build verification is recorded in the historical Beta 5.1 validation record. This does not establish support for every defeated Boss or corpse. No extra damage or healing is added to a zero-HP target.
- Salt has user-confirmed effects and normal recovery in the reported test. The additional Common 205/85 interruption routes have CPU regression coverage only; they have not yet been observed in gameplay, and all Salt/enemy combinations are not confirmed.
- Some non-critical item use remains unfixed. Recovery/buff and ninjutsu items have not all been individually verified; compatibility for specific reported items does not establish complete item support.
- An additional element for the roar is excluded. Needle paralysis strength, exact elemental damage/healing and all airborne variants remain unmeasured/unverified.
- Hot-spring wait samples were about 0.062/0.063 seconds for Hino-Enma and 0.079 seconds for William at the reported pool. These do not establish precise timing equality or the exit branch used in older Hino-Enma traces; other pools remain pending.
- Actual level-up spending, new growth save/load and combat-damage quantification remain pending. Attack scalars are not per-hit damage, and derived ki is not measured final ki-bar capacity. Trainers can independently override runtime values.
- Item shortcuts currently support only slot 2 on the first item shortcut bar; other shortcut slots trigger Hino-Enma skills or moves. Compatible items can also be used from the bag. Sacred Water, the reported locks and Small Spirit Stone are confirmed; not every recovery/buff effect or ninjutsu item has been individually verified.
- Weapon HUD data and isolated rendering paths were checked, but the final on-screen icon still awaits explicit confirmation.
- Individual armor/weapon affixes, elemental effects and measured hit-damage differences have not all been tested.
- Ladder and dojo results cover the reported locations. NPC dialogue and rescue cover the reported cases; other NPCs, repeated rescues, ladders, shrines, scripted events, all mission transitions and interactable variants have not all been verified. Gesture animations may remain laughter. Weapon-switch teaching support does not implement actual Boss weapon switching; native shooting is not implemented.
- Living Weapon retains Hino-Enma's body and moves without William's full startup animation or weapon appearance. Guardian summoning does not reproduce William's additional ki cost. Other guardians, controllers and full combat/transition coverage remain unverified.
- The [CT source](ct/) uses the same scoped hooks; enabling it directly inside Cheat Engine has not been tested. Use either the CT or EXE for a game session. Mixing different versions in one process is not supported.
- Final-public-EXE injection, reload and gameplay evidence are limited to the cases recorded for the release. Offline checks alone do not establish first enable in a fresh game process or complete mission/save coverage.
- This Beta is unsigned with Authenticode. Build provenance and file checksums describe origin and integrity; they are separate from Windows code signing.

## Validation and development

See [Beta 5.2 release record](docs/releases/1.0.0-beta.5.2.md), [build instructions](docs/BUILD.md), [development/release standard](DEVELOPMENT_RELEASE_STANDARD.md) and [credits/components](NOTICE.md). [Beta 5.1 Hotfix 1](docs/releases/1.0.0-beta.5.1.hotfix.1.md) and earlier release records remain historical.

The actual Beta 5.2 source/build results are recorded in [Beta 5.2 validation](docs/validation-beta5.2.json). Public Debug and Release each passed 26 self-checks, 720 current-profile payload comparisons (60 hooks × 12 layouts) and 1,368 complete prior-profile comparisons (55 and 59 hooks × 12 layouts). Source/CT checks passed for 60 hooks, 555 unique local labels, 720 namespace comparisons and six negative guards. Prior-profile recognition verifies complete entry sites and payloads read-only; new installation checks cover executable code and three writable, non-executable data pages. This does not establish a VirtualQuery check of every old installation's live page protection.

The local second-revision EXE separately passed 23 self-checks and 720 payload comparisons, without game access. Its private native-code regression passed 20 tests and 959 CPU comparisons, including 165 comparisons of the 55 unchanged hooks across three layouts. Those local checks are distinct from the public build and from the five-hook temporary gameplay test. The final public EXE has not been gameplay-tested for first enable in a fresh process.

Public portable checks use synthetic records and explicit Win64 stubs; they do not execute the complete game damage/event engine or inventory commit. Private native-code inputs and raw runtime reports are excluded from public source and CI. [Hotfix validation](docs/validation-beta5.1-hotfix1.json), [Beta 5 validation](docs/validation-beta5.json) and earlier evidence retain their historical scope; they are not represented as newly rerun checks. Salt's additional Common 205/85 paths remain CPU-only. Final source commit, shipped hashes and actual publisher are recorded in provenance. Beta 5.2 uses a new immutable tag and release; earlier tags, attachments and historical records remain unchanged.

Character replacement is adapted from the user-supplied **Bryanyora CharacterChange CT**. This tool does not redistribute game assets; original author credits are retained in [NOTICE.md](NOTICE.md).

Report an issue with the game build, mission, interaction object, expected result and actual response. Do not attach saves or process dumps unless you intentionally want to share them.
