import pygame
import random
import subprocess
import threading
import time
import os
import sys
import math
import json
import ctypes
import colorsys

# ==============================================================================
# TOMIS.AI - NEURAL EXPLOSION V22.1 (HD RESTORED + ANTI-STANDBY)
# ==============================================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
LOG_FILE = os.path.join(BASE_DIR, "deployment_log.txt")
LIFETIME_STATS_FILE = os.path.join(BASE_DIR, "node_stats.txt")

# --- SISTEM ---
def set_keep_awake(state):
    if sys.platform == "win32":
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ES_DISPLAY_REQUIRED = 0x00000002
        if state:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED)
        else:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)

def log_action(message):
    try:
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(LOG_FILE, "a") as f:
            f.write(f"[{timestamp}] [Screensaver] {message}\n")
    except: pass

def get_lifetime_tasks():
    if os.path.exists(LIFETIME_STATS_FILE):
        try:
            with open(LIFETIME_STATS_FILE, "r") as f: return int(f.read().strip())
        except: return 0
    return 0

def save_lifetime_tasks(count):
    try:
        with open(LIFETIME_STATS_FILE, "w") as f: f.write(str(count))
    except: pass

class Star:
    def __init__(self, width, height):
        self.pos = pygame.Vector2(random.randint(0, width), random.randint(0, height))
        self.vel = pygame.Vector2(random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15))
        self.base_size = random.uniform(1.0, 2.5)
        self.size = self.base_size
        self.color = [80, 80, 80]
        self.target_color = [80, 80, 80]
        self.is_exploding = False
        self.explosion_timer = 0

    def update(self, width, height, intensity):
        self.pos += self.vel * intensity
        if self.pos.x < 0: self.pos.x = width
        if self.pos.x > width: self.pos.x = 0
        if self.pos.y < 0: self.pos.y = height
        if self.pos.y > height: self.pos.y = 0

        if not self.is_exploding and random.random() < 0.0005:
            self.is_exploding = True
            self.explosion_timer = 1.0
            self.target_color = [random.randint(50, 255) for _ in range(3)]
            self.size = self.base_size * 4

        if self.is_exploding:
            self.explosion_timer -= 0.02
            for i in range(3):
                self.color[i] = int(80 + (self.target_color[i] - 80) * self.explosion_timer)
            self.size = self.base_size + (self.base_size * 3 * self.explosion_timer)
            if self.explosion_timer <= 0:
                self.is_exploding = False
                self.color = [80, 80, 80]
                self.size = self.base_size

    def draw(self, surface):
        pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), int(self.size))

class Screensaver:
    def __init__(self):
        pygame.init()
        info = pygame.display.Info()
        self.width, self.height = info.current_w, info.current_h
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.FULLSCREEN | pygame.DOUBLEBUF)
        pygame.mouse.set_visible(False)
        
        self.last_mouse_pos = pygame.mouse.get_pos()
        self.mouse_sensitivity = 15
        self.stars = [Star(self.width, self.height) for _ in range(160)]
        
        self.text = "ΤΟΜΙΣ.ΑΙ"
        self.text_pos = pygame.Vector2(random.randint(100, self.width-400), random.randint(100, self.height-200))
        self.text_vel = pygame.Vector2(random.uniform(0.2, 0.4), random.uniform(0.2, 0.4))
        self.font_size = int(self.height * 0.06)
        self.branding_grey = 30
        self.branding_dir = 1
        
        self.dash_font = pygame.font.SysFont("consolas", 16)
        self.dash_pos_x = float(self.width - 650)
        self.dash_vel_x = -0.12 
        self.dash_grey = 70
        self.dash_dir = 1
        
        self.master_connected = False
        self.active_containers = []
        self.active_tasks = 0
        self.session_tasks_completed = 0
        self.lifetime_tasks = get_lifetime_tasks()
        self.known_running_pods = set()
        
        pref_fonts = ['georgia', 'timesnewroman', 'palatino', 'serif']
        available = [f for f in pygame.font.get_fonts() if any(p in f for p in pref_fonts)]
        self.font_name = random.choice(available) if available else "arial"
        self.font = pygame.font.SysFont(self.font_name, self.font_size, bold=True)
        self.last_font_change = time.time()

        self.clock = pygame.time.Clock()
        self.running = True
        self.intensity = 1.0
        self.start_time = time.time()

        # ACTIVATE ANTI-STANDBY
        set_keep_awake(True)
        threading.Thread(target=self.manage_ai_node, daemon=True).start()

    def manage_ai_node(self):
        node_name = os.getenv("COMPUTERNAME", "localhost").lower()
        log_action(f"🚀 [INIT] Screensaver V22.1 activat.")
        try:
            subprocess.run(["kubectl", "uncordon", node_name], capture_output=True)
            while self.running:
                res_master = subprocess.run(["kubectl", "cluster-info"], capture_output=True)
                self.master_connected = (res_master.returncode == 0)
                res_pods = subprocess.run(["kubectl", "get", "pods", "--all-namespaces", "--field-selector", "status.phase=Running", "-o", "jsonpath={.items[*].metadata.uid}"], capture_output=True, text=True)
                current_pods = set(res_pods.stdout.split())
                completed = len(self.known_running_pods - current_pods)
                if completed > 0:
                    self.session_tasks_completed += completed
                    self.lifetime_tasks += completed
                    save_lifetime_tasks(self.lifetime_tasks)
                self.known_running_pods = current_pods
                self.active_tasks = len(current_pods)
                res_docker = subprocess.run(["docker", "ps", "--format", "{{.Image}}"], capture_output=True, text=True)
                self.active_containers = list(set(res_docker.stdout.splitlines()))
                self.intensity = 2.0 if self.active_tasks > 0 else 1.0
                time.sleep(4)
            subprocess.run(["kubectl", "cordon", node_name], capture_output=True)
        except Exception as e:
            log_action(f"❌ [ERROR] {str(e)}")

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                    self.running = False
            
            m_pos = pygame.mouse.get_pos()
            if m_pos != self.last_mouse_pos:
                if (pygame.Vector2(m_pos) - pygame.Vector2(self.last_mouse_pos)).length() > 20:
                    self.running = False
            self.last_mouse_pos = m_pos

            self.branding_grey += 0.12 * self.branding_dir
            if self.branding_grey >= 68 or self.branding_grey <= 20: self.branding_dir *= -1
            
            self.dash_grey += 0.25 * self.dash_dir
            if self.dash_grey >= 150 or self.dash_grey <= 50: self.dash_dir *= -1
            
            self.dash_pos_x += self.dash_vel_x
            if self.dash_pos_x <= 50 or self.dash_pos_x >= self.width - 600: self.dash_vel_x *= -1

            self.text_pos += self.text_vel * self.intensity

            # --- RANDARE HD ---
            self.screen.fill((0, 0, 0))

            for i in range(len(self.stars)):
                s1 = self.stars[i]
                s1.update(self.width, self.height, self.intensity)
                for j in range(i + 1, i + 10): 
                    if j >= len(self.stars): break
                    s2 = self.stars[j]
                    dist = s1.pos.distance_to(s2.pos)
                    if dist < 200:
                        alpha = int((1 - (dist / 200)) * 60)
                        pygame.draw.line(self.screen, (alpha, alpha, alpha), s1.pos, s2.pos, 1)
                s1.draw(self.screen)

            text_surf = self.font.render(self.text, True, (int(self.branding_grey),)*3)
            if self.text_pos.x <= 20 or self.text_pos.x >= self.width - text_surf.get_width() - 20: self.text_vel.x *= -1
            if self.text_pos.y <= 20 or self.text_pos.y >= self.height - text_surf.get_height() - 20: self.text_vel.y *= -1
            self.screen.blit(text_surf, self.text_pos)

            uptime = time.strftime("%H:%M:%S", time.gmtime(time.time() - self.start_time))
            master_status = "ON" if self.master_connected else "RECONN"
            stats_text = f"MASTER:{master_status} | ENG:{len(self.active_containers)} | T:{self.active_tasks}N/{self.session_tasks_completed}S/{self.lifetime_tasks}L | {uptime} | WAKE:ACTIVE"
            
            dash_surf = self.dash_font.render(stats_text, True, (int(self.dash_grey),)*3)
            self.screen.blit(dash_surf, (int(self.dash_pos_x), self.height - 30))

            pygame.display.flip()
            self.clock.tick(60)

        set_keep_awake(False)
        pygame.quit(); sys.exit()

if __name__ == "__main__":
    Screensaver().run()
