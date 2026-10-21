# Hand-made positions for tools/scen.py. Systems are (column,row) 0-20, sector = system // 3. Stars are named; capitals are C<color>. [color, sysx, sysy, fleets]
# Capitals (7x7): 2p: color 0 (19,1), color 2 (1,19). 4p: 0 (10,1), 1 (1,10), 2 (19,10), 3 (10,19).
SCEN = {}

# B: 2p, round 12 (12 Actions). The CPU (color 0, last in the round) is 2 VP, the opponent (color 2) 7 VP: eliminated at round end unless it closes the gap to 3 or less.
# CPU: a mesh of 6 stars inside sectors (6,0) and (5,0) (strong stars, only 2 VP). Empty sectors (4,0), (5,1), (6,1) are one Action away (cheap gains),
# and two opponent stars (E1 at sector (4,1), E6 at (6,2)) can be stolen for 4-6 Actions each (+1 me, -1 opponent).
SCEN['elim2'] = dict(n=2, round=12, order=[2, 0], ti=1, stars={
    'B': [0, 19, 2, 0], 'A1': [0, 15, 1, 0], 'A2': [0, 15, 2, 0], 'A3': [0, 16, 1, 0], 'A4': [0, 16, 2, 0], 'A5': [0, 17, 1, 0], 'A6': [0, 18, 1, 0],
    'E1': [2, 12, 4, 0], 'E2': [2, 12, 7, 0], 'E3': [2, 9, 7, 0], 'E4': [2, 6, 7, 0], 'E5': [2, 6, 4, 0], 'E6': [2, 18, 6, 0], 'E7': [2, 18, 9, 0]},
    conns=[['C0', 'B'], ['C0', 'A6'], ['A6', 'A5'], ['A5', 'A3'], ['A3', 'A1'], ['A1', 'A2'], ['A2', 'A4'], ['A4', 'A3'], ['A4', 'A5'], ['A2', 'A3'], ['A4', 'A6'],
           ['E1', 'E2'], ['E2', 'E3'], ['E3', 'E4'], ['E4', 'E5'], ['E6', 'E7']])

# B2: like B, but the cheap targets are NOT free: three opponent singletons with 3 Fleets each sit in sectors (4,0), (5,1), (6,1) next to the CPU mesh
# (cannot be taken, but one new star next to them ties the sector = opponent loses its point, two stars = mine). Two steals (E1, E6) cost 5+ each.
SCEN['elim2b'] = dict(n=2, round=12, order=[2, 0], ti=1, stars={
    'B': [0, 19, 2, 0], 'A1': [0, 15, 1, 0], 'A2': [0, 15, 2, 0], 'A3': [0, 16, 1, 0], 'A4': [0, 16, 2, 0], 'A5': [0, 17, 1, 0], 'A6': [0, 18, 1, 0],
    'E1': [2, 12, 4, 0], 'E2': [2, 12, 7, 0], 'E3': [2, 9, 7, 0], 'E4': [2, 6, 7, 0], 'E6': [2, 18, 6, 0], 'E7': [2, 18, 9, 0],
    'O1': [2, 14, 1, 3], 'O2': [2, 16, 4, 3], 'O3': [2, 19, 4, 3]},
    conns=SCEN['elim2']['conns'][:-2] + [['E4', 'E3'], ['E6', 'E7']])

# A: 4p, round 10 (10 Actions). Leader (color 0, 9 VP) far ahead of colors 2 (3), 3 (4), 1 (4). The CPU is color 1 (west), moving last (order 0,3,1,2 -> ti 2).
# Leader's western sectors (2,0), (2,1), (1,0) are held by single stars (weakly connected) that the CPU's west cluster can reach for 3-5 Actions;
# there are also free sectors to the south-west for cheap expansion.
SCEN['lead4'] = dict(n=4, round=10, order=[0, 3, 1, 2], ti=2, stars={
    'L1': [0, 7, 1, 0], 'L2': [0, 13, 1, 0], 'L3': [0, 10, 4, 0], 'L4': [0, 7, 4, 0], 'L5': [0, 13, 4, 0], 'L6': [0, 4, 1, 0], 'L7': [0, 16, 1, 0], 'L8': [0, 10, 7, 0],
    'W1': [1, 1, 7, 0], 'W2': [1, 1, 13, 0], 'W3': [1, 4, 10, 0], 'W4': [1, 4, 7, 0], 'W5': [1, 4, 4, 0], 'W6': [1, 1, 6, 0],
    'S1': [3, 10, 16, 0], 'S2': [3, 7, 19, 0], 'S3': [3, 13, 19, 0], 'S4': [3, 13, 16, 0],
    'R1': [2, 19, 7, 0], 'R2': [2, 16, 10, 0], 'R3': [2, 16, 13, 0]},
    conns=[['C0', 'L1'], ['C0', 'L2'], ['C0', 'L3'], ['L3', 'L4'], ['L3', 'L5'], ['L1', 'L6'], ['L2', 'L7'], ['L3', 'L8'],
           ['C1', 'W1'], ['C1', 'W2'], ['C1', 'W3'], ['W3', 'W4'], ['W4', 'W5'], ['W1', 'W6'], ['W4', 'W6'], ['W5', 'W6'],
           ['C3', 'S1'], ['C3', 'S2'], ['C3', 'S3'], ['S3', 'S4'], ['C2', 'R1'], ['C2', 'R2'], ['R2', 'R3']], opp=0)
