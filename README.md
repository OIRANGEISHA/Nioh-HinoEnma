# Nioh Hino-Enma Beta 6.1.4

[简体中文](README.zh-CN.md)

Beta 6.1.4 (`1.0.0-beta.6.1.4`) for Steam Nioh: Complete Edition 1.24.08. Download the standalone Windows x64 EXE or complete committed-source ZIP from the [Beta 6.1.4 release](https://github.com/OIRANGEISHA/Nioh-HinoEnma/releases/tag/v1.0.0-beta.6.1.4). These are the only two Release attachments.

Adds a general ninjutsu/Onmyo action dispatcher using native item categories, retaining the game's effects and resource consumption. Fixes Kunai casting without a projectile, consecutive throwing, and injury transitions that incorrectly selected Hino-Enma's taunt, flight or roar. Kunai projectiles, repeated use, injury recovery and subsequent movement/attacks were confirmed in the running game.

Retains all Beta 6.1.3 repairs, including Sticky Pot, Dispersal recasting, the nine talismans and Soul Release. Soul Release still requires at least 300 weapon familiarity and uses native familiarity consumption and projectile behavior.

Restart the game, stop at the title menu, run the EXE and enable Hino-Enma, then continue. Repeat after each game restart. No Python or Cheat Engine is required for the EXE. Use compatible items from inventory or shortcut **2 on the first item bar**. Release and press again after each animation ends. Main keys: **1** life drain, **5** roar, **9** Living Weapon, **F6** purification. Other item slots retain Hino-Enma's skills.

Levels 0–750 still map linearly to native growth indices 1–4525. From level 401, the Boss HP basis is doubled and main attack multiplied by 1.2, before native player, equipment and Focus bonuses. Ki and defense use native curves; a higher native Boss index is retained. Earlier guardian, Living Weapon, element, preview and interaction fixes are preserved.

**Some ninjutsu, Onmyo magic and items remain unsupported or unverified.** Offline dispatch coverage includes 13 categories and 132 definitions, not 132 gameplay-tested effects. Transformations, death triggers, Soul Purge, Earthfolding, persistent objects and unusual resource costs need individual validation; see the [special-case audit](docs/general-jutsu-special-cases.json). The exact new EXE has not undergone a complete game-restart test.

Usage, keys, CT, build tools and verification records are in the source archive. See [release notes](docs/releases/1.0.0-beta.6.1.4.md), [build instructions](docs/BUILD.md), [keys](docs/键位说明.md) and [credits](NOTICE.md).
