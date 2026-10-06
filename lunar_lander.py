#!/usr/bin/env python3
"""lunar-lander — 登月舱物理小游戏。重力 + 主/侧推力 + 燃料，安全着陆挑战。纯标准库。"""

import argparse
import math
import random
import sys

GRAVITY = 1.6          # 月面重力 m/s^2
MAIN_THRUST = 3.2      # 主推进加速度
SIDE_THRUST = 1.6      # 侧推进加速度
DT = 0.1               # 物理步长（秒）
FUEL_START = 100.0
MAIN_BURN = 1.2        # 主推力每秒燃料
SIDE_BURN = 0.5
MAX_LAND_VY = 2.5      # 安全着陆最大垂直速度
MAX_LAND_VX = 2.0      # 安全着陆最大水平速度
PAD_X = 40.0           # 着陆平台中心（米）
PAD_W = 10.0           # 平台宽度


class Lander:
    """登月舱物理核心。坐标系：x 右为正，y 高度为正。"""

    def __init__(self, seed=None):
        rng = random.Random(seed)
        self.x = rng.uniform(10.0, 70.0)
        self.y = 60.0
        self.vx = rng.uniform(-5.0, 5.0)
        self.vy = 0.0
        self.fuel = FUEL_START
        self.over = False
        self.result = None   # 'landed' / 'crashed' / 'out_of_fuel'（燃料耗尽不算结束，只是没推力）
        self.frames = 0

    def step(self, main=False, left=False, right=False):
        """推进一帧。返回 True 表示本帧着陆/坠毁（游戏结束）。"""
        if self.over:
            return True
        ax, ay = 0.0, -GRAVITY
        burn = 0.0
        if main and self.fuel > 0:
            ay += MAIN_THRUST
            burn += MAIN_BURN
        if left and self.fuel > 0:
            ax -= SIDE_THRUST
            burn += SIDE_BURN
        if right and self.fuel > 0:
            ax += SIDE_THRUST
            burn += SIDE_BURN
        self.fuel = max(0.0, self.fuel - burn * DT)
        self.vx += ax * DT
        self.vy += ay * DT
        self.x += self.vx * DT
        self.y += self.vy * DT
        self.frames += 1
        if self.y <= 0:
            self.y = 0
            self.over = True
            on_pad = abs(self.x - PAD_X) <= PAD_W / 2
            gentle = abs(self.vy) <= MAX_LAND_VY and abs(self.vx) <= MAX_LAND_VX
            self.result = 'landed' if (on_pad and gentle) else 'crashed'
            return True
        return False

    def status(self):
        return (f"高度 {self.y:6.1f}m  水平 {self.x:6.1f}m  "
                f"垂直速度 {self.vy:+6.1f}m/s  水平速度 {self.vx:+6.1f}m/s  "
                f"燃料 {self.fuel:5.1f}")


def auto_play(seed=None, verbose=False, max_frames=5000):
    """简单 PID 式控制器：先对准平台，再控制下降速度。"""
    g = Lander(seed)
    while not g.over and g.frames < max_frames:
        # 水平：朝平台加速/减速
        dx = PAD_X - g.x
        left = right = False
        if abs(dx) > 1.0:
            # 期望水平速度与距离成正比
            want_vx = max(-6.0, min(6.0, dx * 0.3))
            if g.vx > want_vx + 0.5:
                left = True
            elif g.vx < want_vx - 0.5:
                right = True
        # 垂直：期望下降速度随高度减小
        want_vy = -max(1.0, min(8.0, g.y * 0.25))
        main = g.vy < want_vy - 0.3
        # 接近地面时强制减速到安全范围
        if g.y < 8.0 and (g.vy < -MAX_LAND_VY + 0.3 or abs(g.vx) > MAX_LAND_VX - 0.3):
            main = True
        g.step(main=main, left=left, right=right)
        if verbose and g.frames % 50 == 0:
            print(g.status(), f"主推 {'开' if main else '关'}")
    if verbose:
        print(g.status())
    return g


def render(g):
    """文本渲染：高度条 + 平台示意。"""
    bar_h = 12
    lvl = max(0, min(bar_h - 1, int(g.y / 70.0 * bar_h)))
    lines = []
    for i in range(bar_h - 1, -1, -1):
        mark = " 🚀" if i == lvl else "   "
        lines.append(f"{mark} |")
    pad_l = int((PAD_X - PAD_W / 2) / 80 * 20)
    pad_r = int((PAD_X + PAD_W / 2) / 80 * 20)
    ground = "".join("=" if pad_l <= i <= pad_r else "_" for i in range(20))
    lines.append("   +" + ground)
    return "\n".join(lines)


def play_interactive(seed=None):
    if not sys.stdin.isatty():
        print("交互模式需要终端；请使用 --auto 观看演示。", file=sys.stderr)
        return 2
    g = Lander(seed)
    print("登月舱：每行输入指令后回车（w=主推 a=左 d=右，可组合如 wad，空行=滑行，q=退出）")
    print(f"着陆平台在 x={PAD_X}±{PAD_W / 2}m，安全速度 |vy|<={MAX_LAND_VY}, |vx|<={MAX_LAND_VX}")
    while not g.over:
        print(render(g))
        print(g.status())
        try:
            cmd = input("> ").strip().lower()
        except EOFError:
            break
        if cmd == "q":
            break
        g.step(main="w" in cmd, left="a" in cmd, right="d" in cmd)
    print(render(g))
    print(g.status())
    if g.result == "landed":
        print(f"🎉 成功着陆！剩余燃料 {g.fuel:.1f}")
    elif g.result == "crashed":
        print("💥 坠毁了……")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="登月舱物理小游戏（纯标准库）")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--auto", action="store_true", help="自动演示（简单控制器）")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args(argv)
    if args.auto:
        g = auto_play(seed=args.seed, verbose=args.verbose)
        if g.result == "landed":
            print(f"自动演示结束：成功着陆，剩余燃料 {g.fuel:.1f}，用时 {g.frames * DT:.1f}s")
        elif g.result == "crashed":
            print(f"自动演示结束：坠毁（x={g.x:.1f}, vy={g.vy:.1f}, vx={g.vx:.1f}），剩余燃料 {g.fuel:.1f}")
        else:
            print(f"自动演示结束：超时未着陆（y={g.y:.1f}），剩余燃料 {g.fuel:.1f}")
        return 0
    return play_interactive(seed=args.seed)


if __name__ == "__main__":
    sys.exit(main())
