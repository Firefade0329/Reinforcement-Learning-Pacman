"""Independent oracle for n-step targets.  Deliberately imports NOTHING from pacman_rl: it re-derives, from the
definition and with exact rational arithmetic, which training samples an n-step replay must hold after every
round of environment steps and what TD target each one must receive.

    G = sum_{i<h} gamma^i * r_i  +  gamma^h * Q_target(s_h, argmax_a Q_online(s_h, a))

with h = min(n, steps left in the episode).  A true terminal ends the sum (no bootstrap); a time-limit
truncation bootstraps from the real final state; an episode still running contributes only complete n-windows.
Structure differs on purpose from the replay under test (no queues, no flush: closed-form per transition).
"""
from __future__ import annotations

import random
from fractions import Fraction


def fr(x):
    return Fraction(x).limit_denominator(1 << 20) if isinstance(x, float) else Fraction(x)


def expected_samples(envs, n, gamma, q_online, q_target, double=True):
    """envs: list (per environment) of episodes; episode = list of [s, a, r, s2, status].  All environments are
    stepped once per round, so the r-th step of an environment (counted over its episodes) happens in round r.
    Returns (samples, counts): samples = sorted list of (s, a, ret, disc, s2_boot, y); counts[r] = number of samples
    that must be stored once round r has been processed."""
    gamma = fr(gamma)
    rounds = sum(len(ep) for ep in envs[0])
    emitted = []  # (round, sample)
    for ep_list in envs:
        assert sum(len(ep) for ep in ep_list) == rounds, "all environments must take the same number of steps"
        r0 = 0
        for ep in ep_list:
            m = len(ep)
            status = ep[-1][4] if m else ""
            finished = status in ("terminated", "truncated")
            for t in range(m):
                if not finished and t + n > m:
                    continue  # window not complete yet: still pending
                h = min(n, m - t)
                ret = sum(gamma ** i * fr(ep[t + i][2]) for i in range(h))
                if t + h < m or (t + h == m and not finished):  # window ends inside / at the end of a running episode
                    boot, disc = ep[t + h - 1][3], gamma ** h
                elif status == "terminated":
                    boot, disc = ep[-1][3], Fraction(0)
                else:  # truncated: bootstrap from the real final state
                    boot, disc = ep[-1][3], gamma ** h
                y = ret
                if disc != 0:
                    qo, qt = q_online[boot], q_target[boot]
                    a_star = max(range(len(qo)), key=lambda a: (qo[a], -a)) if double else max(range(len(qt)), key=lambda a: (qt[a], -a))
                    y = ret + disc * fr(qt[a_star])
                emitted.append((r0 + min(t + h, m) - 1, (ep[t][0], ep[t][1], ret, disc, boot, y)))
            r0 += m
    counts = [sum(1 for rd, _ in emitted if rd <= r) for r in range(rounds)]
    return sorted(s for _, s in emitted), counts


def random_case(seed, n_envs=3, rounds=40, p_end=0.12, p_trunc=0.4):
    """Random interleaved scripts with globally unique state ids (so any cross-environment / cross-episode leak
    changes a state id) and small integer rewards.  Returns (envs, q_online, q_target, n_states)."""
    rng = random.Random(seed)
    sid = iter(range(10_000))
    envs = []
    for _ in range(n_envs):
        eps, cur = [], []
        s = next(sid)
        for r in range(rounds):
            s2 = next(sid)
            last = r == rounds - 1
            ends = (not last or rng.random() < 0.5) and rng.random() < p_end
            status = ("truncated" if rng.random() < p_trunc else "terminated") if ends else ""
            cur.append([s, rng.randrange(5), rng.choice([-10, -1, 0, 1, 2, 4, 8]), s2, status])
            if ends:
                eps.append(cur)
                cur, s = [], next(sid)  # a reset lands in a state nobody else uses
            else:
                s = s2
        if cur:
            eps.append(cur)
        else:
            eps.append([])  # the environment was just reset when the stream stops
        envs.append(eps)
    states = {st[3] for eps in envs for ep in eps for st in ep}
    q_online, q_target = {}, {}
    for st in states:
        row = rng.sample(range(-20, 21), 5)  # distinct values: no argmax ties
        q_online[st] = row
        q_target[st] = [rng.randrange(-30, 31) for _ in range(5)]
    return envs, q_online, q_target
