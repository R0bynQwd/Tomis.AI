import json
import os
import random
import sys
import threading
import time
from urllib.request import urlopen

import pygame

CONFIG_FILE = "config.json"
LIFETIME_STATS_FILE = "node_stats.txt"
TASK_EMULATION_FILE = "task_emulation.json"
ACTIVE_STATES = {"Running", "Pending", "ContainerCreating", "CrashLoopBackOff"}
MASTER_FALLBACK_URLS = [
    "http://192.168.1.104:28001/stats",
    "http://100.78.68.58:28001/stats",
]


def get_stats():
    if os.path.exists(LIFETIME_STATS_FILE):
        try:
            with open(LIFETIME_STATS_FILE, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except Exception:
            pass
    return 0


def count_active_tasks():
    emulated = 0
    if os.path.exists(TASK_EMULATION_FILE):
        try:
            with open(TASK_EMULATION_FILE, "r", encoding="utf-8") as f:
                emulated = int(json.load(f).get("active_tasks", 0))
        except Exception:
            emulated = 0

    try:
        import subprocess

        res = subprocess.run(["kubectl", "get", "pods", "-A", "--no-headers"], capture_output=True, text=True)
        if res.returncode != 0:
            return emulated
        count = 0
        for line in res.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[3] in ACTIVE_STATES:
                count += 1
        return max(count, emulated)
    except Exception:
        return emulated


def resolve_master_urls():
    urls = list(MASTER_FALLBACK_URLS)
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            ip = cfg.get("master_ip")
            if ip:
                urls.append(f"http://{ip}:28001/stats")
    except Exception:
        pass
    seen = set()
    ordered = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            ordered.append(u)
    return ordered


def test_master_online():
    for url in resolve_master_urls():
        try:
            r = urlopen(url, timeout=2.5)
            if r.getcode() == 200:
                return True
        except Exception:
            pass
    return False


def make_star(w, h):
    angle = random.uniform(0, 6.283185307)
    speed = random.uniform(0.025, 0.13)
    depth = random.uniform(0.25, 1.0)
    return {
        "x": random.uniform(0, w),
        "y": random.uniform(0, h),
        "vx": speed * (0.4 + depth) * (1 if random.random() > 0.5 else -1),
        "vy": speed * (0.4 + depth) * (1 if random.random() > 0.5 else -1),
        "d": depth,
        "r": random.uniform(0.8, 2.3),
        "phase": random.uniform(0, 6.283185307),
        "color": random.choice([(90, 167, 255), (112, 255, 216), (159, 107, 255), (232, 240, 255)]),
    }


class Screensaver:
    def __init__(self):
        pygame.init()
        info = pygame.display.Info()
        self.w, self.h = info.current_w, info.current_h
        self.screen = pygame.display.set_mode((self.w, self.h), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        pygame.mouse.set_visible(False)

        self.running = True
        self.start = time.time()
        self.frame = 0
        self.master_on = False
        self.last_master_ok = 0.0
        self.active_tasks = 0
        self.lifetime = get_stats()

        count = max(100, min(320, int((self.w * self.h) / 15000)))
        self.stars = [make_star(self.w, self.h) for _ in range(count)]
        self.links = []
        self._rebuild_links(force=True)
        self.font_title = pygame.font.SysFont("segoeui", 22, bold=True)
        self.font_body = pygame.font.SysFont("segoeui", 16)
        self.clock = pygame.time.Clock()
        threading.Thread(target=self.monitor, daemon=True).start()

    def _rebuild_links(self, force=False):
        if (not force) and (self.frame % 7 != 0):
            return
        self.links = []
        n = len(self.stars)
        span = 3 + int((1.0 + __import__("math").sin(self.frame * 0.01)) * 2)
        for i in range(n):
            hops = random.randint(1, span)
            for k in range(1, hops + 1):
                j = (i + k * random.randint(1, 5)) % n
                self.links.append((i, j))

    def monitor(self):
        while self.running:
            if test_master_online():
                self.last_master_ok = time.time()
            # Keep ON for a short grace window to avoid OFF flicker on transient timeouts.
            self.master_on = (time.time() - self.last_master_ok) <= 30
            self.active_tasks = count_active_tasks()
            time.sleep(5)

    def draw_background(self):
        step = 14
        for y in range(0, self.h, step):
            shade = int(5 + (float(y) / self.h) * 14)
            col = (shade, shade + 4, shade + 18)
            pygame.draw.rect(self.screen, col, (0, y, self.w, step))

    def draw_stars(self):
        import math

        self._rebuild_links()
        for i, j in self.links:
            a = self.stars[i]
            b = self.stars[j]
            dist = math.hypot(a["x"] - b["x"], a["y"] - b["y"])
            if dist < 170:
                pygame.draw.aaline(self.screen, (42, 134, 255), (a["x"], a["y"]), (b["x"], b["y"]))

        t = time.time() - self.start
        for s in self.stars:
            s["x"] += s["vx"]
            s["y"] += s["vy"]
            if s["x"] < -12:
                s["x"] = self.w + 12
            if s["x"] > self.w + 12:
                s["x"] = -12
            if s["y"] < -12:
                s["y"] = self.h + 12
            if s["y"] > self.h + 12:
                s["y"] = -12

            tw = 0.72 + 0.28 * math.sin(t * (0.8 + s["d"] * 0.5) + s["phase"])
            r = max(1, int(s["r"] * (0.85 + s["d"] * 0.9) * tw))
            x, y = int(s["x"]), int(s["y"])
            trail_x = int(s["x"] - s["vx"] * 16)
            trail_y = int(s["y"] - s["vy"] * 16)
            pygame.draw.aaline(self.screen, s["color"], (trail_x, trail_y), (x, y))
            pygame.draw.circle(self.screen, s["color"], (x, y), r + 1)
            pygame.draw.circle(self.screen, (244, 248, 255), (x, y), r)

    def draw_panel(self):
        panel_w = min(520, self.w - 40)
        panel_h = 120
        x0, y0 = 20, self.h - panel_h - 20
        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((10, 16, 27, 210))
        pygame.draw.rect(panel, (45, 164, 255), panel.get_rect(), 2)
        panel.blit(self.font_title.render("TOMIS.AI // NEURAL CORE", True, (201, 232, 255)), (16, 14))
        panel.blit(self.font_body.render(f"MASTER: {'ON' if self.master_on else 'OFF'}", True, (232, 232, 232)), (16, 46))
        panel.blit(self.font_body.render(f"ACTIVE TASKS: {self.active_tasks}", True, (232, 232, 232)), (16, 70))
        panel.blit(self.font_body.render(f"LIFETIME: {self.lifetime}", True, (168, 191, 212)), (16, 94))
        self.screen.blit(panel, (x0, y0))

    def run(self):
        while self.running:
            for e in pygame.event.get():
                if e.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    self.running = False
            self.frame += 1
            self.screen.fill((0, 0, 0))
            self.draw_background()
            self.draw_stars()
            self.draw_panel()
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Screensaver().run()
