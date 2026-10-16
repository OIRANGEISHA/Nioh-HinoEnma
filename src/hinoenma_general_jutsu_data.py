"""Native category contracts and six additional common action schedules.

Read-only capture 2026-10-15, Steam1.24.08; every resource reread for stability.
The category selects a family; item ID/effects/spawn stay owned by the game.
"""

FAMILIES = {4: (165, 103, ((1, 5), (1, 65541), (3585, 65541), (3586, 5), (3586, 32775))),
 5: (166, 106, ((3586, 5),)),
 6: (982, 120, ((1, 65541), (3586, 5))),
 7: (41, 110, ((1, 65541), (3, 7), (3841, 81989), (3842, 5), (3842, 1029), (3842, 16453))),
 9: (42, 111, ((3842, 5),)),
 11: (986, 104, ((3586, 5),)),
 16: (605, 125, ((3586, 5),)),
 18: (606, 122, ((3586, 5),)),
 19: (607, 124, ((3586, 5),)),
 20: (608, 123, ((3586, 5),)),
 22: (610, 111, ((1, 73733), (3842, 8197))),
 23: (611, 110, ((3842, 5),)),
 25: (1165, 111, ((3842, 5),))}

NEW_SCHEDULES = {166: '12000a00ffff1f002400ffff140000000a00210014000200ffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
 605: '12001300ffff1f004000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
 606: 'ffff0000ffff13003700ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
 607: '12000a00ffff1f005f00ffff140002000f00a0000000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
 608: '12000a00ffff1f003200ffff770028000a00ffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff',
 986: '12000200ffff1f001800ffff140000000f00ffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffffffff0000ffff'}

NEW_EVENT_GUARDS = {166: ((18, 6, -1, 22, 255, 255, -1),
       (20, 255, -1, -1, 255, 18, -1),
       (31, 5, -1, -1, 255, 255, -1),
       (33, 255, -1, -1, 255, 255, -1)),
 605: ((18, 6, -1, 22, 255, 255, -1), (31, 5, -1, -1, 255, 255, -1)),
 606: ((19, 255, -1, -1, 0, 255, -1),),
 607: ((18, 6, -1, 22, 255, 255, -1),
       (20, 255, -1, -1, 255, 18, -1),
       (31, 5, -1, -1, 255, 255, -1),
       (160, 255, -1, -1, 255, 255, -1)),
 608: ((18, 6, -1, 22, 255, 255, -1), (31, 5, -1, -1, 255, 255, -1), (119, 255, -1, -1, 255, 255, -1)),
 986: ((18, 6, -1, 22, 255, 255, -1), (20, 255, -1, -1, 255, 18, -1), (31, 5, -1, -1, 255, 255, -1))}
