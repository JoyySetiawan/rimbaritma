import pygame
import sys
import os

# ==========================================
#         INISIALISASI & KONFIGURASI
# ==========================================
pygame.init()

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Rimbatritma: Petualangan Koding")

# --- Palet Warna (RGB) ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (39, 174, 96) 
BLUE  = (52, 152, 219) 
LIGHT_BLUE = (135, 206, 235) 
WOOD_COLOR = (205, 133, 63) 
WOOD_HOVER = (222, 184, 135) 
GRAY  = (149, 165, 166)
RED = (231, 76, 60)
YELLOW = (241, 196, 15)
DARK_GREEN = (46, 204, 113) 

# --- Kecepatan Frame ---
clock = pygame.time.Clock()
FPS = 60

# --- State Game ---
STATE_MENU = "menu"
STATE_MAP = "map"
STATE_COMBAT = "combat"
current_state = STATE_MENU 

# ==========================================
#              FUNGSI PENDUKUNG
# ==========================================
def draw_text(text, font_size, x, y, color=BLACK, center=False):
    font = pygame.font.SysFont("Arial", font_size, bold=True)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)
    screen.blit(text_surface, text_rect)

def draw_hp_bar(screen, x, y, hp, max_hp, width=120, height=15):
    if hp < 0: hp = 0
    fill_width = int((hp / max_hp) * width)
    
    pygame.draw.rect(screen, RED, (x, y, width, height))
    pygame.draw.rect(screen, DARK_GREEN, (x, y, fill_width, height))
    pygame.draw.rect(screen, WHITE, (x, y, width, height), 2)

# ==========================================
#             LOGIKA MODE: MAIN MENU
# ==========================================
class MainMenu:
    def __init__(self):
        self.btn_new_game = pygame.Rect(300, 300, 200, 60)
        self.btn_exit = pygame.Rect(300, 400, 200, 60)

    def update(self, events):
        global current_state, running
        mouse_pos = pygame.mouse.get_pos()
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.btn_new_game.collidepoint(mouse_pos):
                    current_state = STATE_MAP 
                elif self.btn_exit.collidepoint(mouse_pos):
                    running = False 

    def draw(self):
        screen.fill(LIGHT_BLUE) 
        title_rect = pygame.Rect(150, 80, 500, 120)
        pygame.draw.rect(screen, WOOD_COLOR, title_rect, border_radius=15)
        pygame.draw.rect(screen, BLACK, title_rect, 5, border_radius=15)
        draw_text("RIMBATRITMA", 50, SCREEN_WIDTH // 2, 140, WHITE, center=True)

        mouse_pos = pygame.mouse.get_pos()
        color_new = WOOD_HOVER if self.btn_new_game.collidepoint(mouse_pos) else WOOD_COLOR
        pygame.draw.rect(screen, color_new, self.btn_new_game, border_radius=10)
        pygame.draw.rect(screen, BLACK, self.btn_new_game, 3, border_radius=10)
        draw_text("NEW GAME", 24, self.btn_new_game.centerx, self.btn_new_game.centery, BLACK, center=True)

        color_exit = WOOD_HOVER if self.btn_exit.collidepoint(mouse_pos) else WOOD_COLOR
        pygame.draw.rect(screen, color_exit, self.btn_exit, border_radius=10)
        pygame.draw.rect(screen, BLACK, self.btn_exit, 3, border_radius=10)
        draw_text("EXIT", 24, self.btn_exit.centerx, self.btn_exit.centery, BLACK, center=True)

# ==========================================
#             LOGIKA MODE: MAP
# ==========================================
class WorldMap:
    def __init__(self):
        self.levels = [
            {"id": 1, "pos": (150, 450)},
            {"id": 2, "pos": (200, 250)},
            {"id": 3, "pos": (350, 150)},
            {"id": 4, "pos": (500, 200)},
            {"id": 5, "pos": (650, 300)}, 
        ]
        self.player_pos_index = 0 
        self.node_radius = 20

    def update(self, events):
        global current_state
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RIGHT:
                    if self.player_pos_index < len(self.levels) - 1:
                        self.player_pos_index += 1
                elif event.key == pygame.K_LEFT:
                    if self.player_pos_index > 0:
                        self.player_pos_index -= 1
                elif event.key == pygame.K_SPACE:
                    current_state = STATE_COMBAT 
                elif event.key == pygame.K_ESCAPE:
                    current_state = STATE_MENU 

    def draw(self):
        screen.fill(BLUE) 
        pygame.draw.ellipse(screen, GREEN, (50, 100, 700, 450)) 
        
        for i in range(len(self.levels) - 1):
            pygame.draw.line(screen, BLACK, self.levels[i]["pos"], self.levels[i+1]["pos"], 2)
            
        for level in self.levels:
            color = WHITE
            if level["id"] == 5: color = RED
            pygame.draw.circle(screen, color, level["pos"], self.node_radius)
            pygame.draw.circle(screen, BLACK, level["pos"], self.node_radius, 2)
            level_text = str(level["id"]) if level["id"] < 5 else "B"
            draw_text(level_text, 20, level["pos"][0], level["pos"][1], center=True)
            
        p_x, p_y = self.levels[self.player_pos_index]["pos"]
        pygame.draw.polygon(screen, YELLOW, [(p_x, p_y - 35), (p_x - 10, p_y - 50), (p_x + 10, p_y - 50)])
        draw_text("Panah L/R: Memilih | SPASI: Masuk | ESC: Main Menu", 20, SCREEN_WIDTH // 2, 20, WHITE, center=True)

# ==========================================
#           LOGIKA MODE: COMBAT
# ==========================================
class CombatScene:
    def __init__(self):
        self.arena_width = 530
        self.arena_rect = pygame.Rect(0, 0, self.arena_width, SCREEN_HEIGHT)
        self.ui_rect = pygame.Rect(self.arena_width, 0, SCREEN_WIDTH - self.arena_width, SCREEN_HEIGHT)
        
        # --- BARU: MEMUAT GAMBAR LATAR BELAKANG ARENA ---
        try:
            bg_asli = pygame.image.load("combat_bg.png")
            # Menyesuaikan ukuran background dengan area 2/3 layar (Arena)
            self.arena_bg = pygame.transform.scale(bg_asli, (self.arena_width, SCREEN_HEIGHT))
            self.bg_loaded = True
        except FileNotFoundError:
            self.bg_loaded = False
        
        # --- MEMUAT GAMBAR PEMAIN ---
        try:
            gambar_asli = pygame.image.load("kesatria.png")
            lebar_asli = gambar_asli.get_width()
            tinggi_asli = gambar_asli.get_height()
            
            target_tinggi = 160 
            rasio = target_tinggi / tinggi_asli
            lebar_baru = int(lebar_asli * rasio)
            
            self.player_image = pygame.transform.scale(gambar_asli, (lebar_baru, target_tinggi))
            self.image_loaded = True
            
            self.player_width = lebar_baru # Simpan lebar untuk rumus HP Bar
            self.player_x = (self.arena_width // 3) - (lebar_baru // 2) - 30
            self.player_y = 320
        except FileNotFoundError:
            self.image_loaded = False 
            self.player_width = 80
            self.player_x, self.player_y = 90, 320
            
        # --- MEMUAT GAMBAR MUSUH ---
        try:
            gambar_musuh_asli = pygame.image.load("monster_slime.png")
            lebar_musuh_asli = gambar_musuh_asli.get_width()
            tinggi_musuh_asli = gambar_musuh_asli.get_height()
            
            target_tinggi_musuh = 120 
            rasio_musuh = target_tinggi_musuh / tinggi_musuh_asli
            lebar_musuh_baru = int(lebar_musuh_asli * rasio_musuh)
            
            self.enemy_image = pygame.transform.scale(gambar_musuh_asli, (lebar_musuh_baru, target_tinggi_musuh))
            self.enemy_image_loaded = True
            
            self.enemy_width = lebar_musuh_baru # Simpan lebar untuk rumus HP Bar
            self.enemy_x = ((self.arena_width // 3) * 2) - (lebar_musuh_baru // 2) + 30
            self.enemy_y = 360
        except FileNotFoundError:
            self.enemy_image_loaded = False
            self.enemy_width = 120 # Diameter lingkaran (radius 60 * 2)
            self.enemy_x, self.enemy_y = 300, 360
        
        # Status Pertarungan
        self.player_hp = 100
        self.enemy_hp = 100
        self.slime_damage_taken = 0
        self.player_damage_taken = 0
        
        # Input Koding
        self.input_text = ""
        self.target_code = "print(\"Serang\")"
        self.feedback_text = ""
        
        # Sistem Giliran
        self.enemy_turn_delay = 0 
        self.is_enemy_turn = False 
        
        # Sistem Kemenangan
        self.is_victory = False
        self.xp_reward = 50   
        self.gold_reward = 20 

    def update(self, events):
        global current_state
        
        if self.is_victory:
            for event in events:
                if event.type == pygame.KEYDOWN and (event.key == pygame.K_RETURN or event.key == pygame.K_SPACE):
                    self.player_hp = 100
                    self.enemy_hp = 100
                    self.is_victory = False
                    self.input_text = ""
                    self.feedback_text = ""
                    self.slime_damage_taken = 0
                    current_state = STATE_MAP
            return 

        if self.is_enemy_turn and self.enemy_turn_delay > 0:
            self.enemy_turn_delay -= 1 
            if self.enemy_turn_delay == 0:
                self.musuh_menyerang()

        if not self.is_enemy_turn:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.player_hp = 100
                        self.enemy_hp = 100
                        self.input_text = ""
                        self.feedback_text = ""
                        self.slime_damage_taken = 0
                        self.player_damage_taken = 0
                        current_state = STATE_MAP
                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        self.check_code()
                    else:
                        if len(self.input_text) < 25:
                            self.input_text += event.unicode

    def check_code(self):
        if self.input_text == self.target_code:
            self.enemy_hp -= 20
            self.slime_damage_taken = 20
            self.player_damage_taken = 0 
            self.input_text = ""
            
            if self.enemy_hp <= 0:
                self.enemy_hp = 0 
                self.is_victory = True 
                self.feedback_text = "Menang! (ENTER)"
            else:
                self.feedback_text = "Berhasil menyerang!"
                self.is_enemy_turn = True
                self.enemy_turn_delay = 60 
        else:
            self.feedback_text = "Kode Salah! Awas!"
            self.slime_damage_taken = 0
            self.player_damage_taken = 0
            self.input_text = ""
            self.is_enemy_turn = True
            self.enemy_turn_delay = 60

    def musuh_menyerang(self):
        damage_musuh = 10
        self.player_hp -= damage_musuh
        self.player_damage_taken = damage_musuh
        self.feedback_text = f"Terkena {damage_musuh} DMG!"
        self.slime_damage_taken = 0 
        self.is_enemy_turn = False 

    def draw(self):
        screen.fill(GRAY)
        
        # --- MENGGAMBAR ARENA KIRI ---
        # Cek apakah gambar background berhasil di-load
        if self.bg_loaded:
            screen.blit(self.arena_bg, (0, 0)) # Pasang gambar background
            pygame.draw.rect(screen, BLACK, self.arena_rect, 4) # Bingkai hitam
        else:
            pygame.draw.rect(screen, GREEN, self.arena_rect) # Fallback warna hijau
            pygame.draw.rect(screen, BLACK, self.arena_rect, 4)
        
        # Konstanta lebar HP bar
        bar_width = 120 
        
        # --- MENAMPILKAN PEMAIN ---
        if self.image_loaded:
            screen.blit(self.player_image, (self.player_x, self.player_y))
        else:
            pygame.draw.rect(screen, WHITE, pygame.Rect(self.player_x, self.player_y, self.player_width, 160))
            
        # Rumus Center Pemain: Posisi X Pemain + (Lebar Pemain / 2)
        player_center_x = self.player_x + (self.player_width // 2)
        
        # Gambar HP Bar Pemain (di tengah atas kepala)
        draw_hp_bar(screen, player_center_x - (bar_width // 2), self.player_y - 25, self.player_hp, 100, bar_width)
        
        if self.player_damage_taken > 0:
            draw_text(f"-{self.player_damage_taken}", 24, player_center_x, self.player_y - 55, RED, center=True)
            
        # --- MENAMPILKAN MUSUH ---
        if self.enemy_image_loaded:
            screen.blit(self.enemy_image, (self.enemy_x, self.enemy_y))
        else:
            pygame.draw.circle(screen, BLUE, (self.enemy_x + 60, self.enemy_y + 60), 60)
            
        # Rumus Center Musuh: Posisi X Musuh + (Lebar Musuh / 2)
        enemy_center_x = self.enemy_x + (self.enemy_width // 2)
        
        # Gambar HP Bar Musuh (di tengah atas kepala)
        draw_hp_bar(screen, enemy_center_x - (bar_width // 2), self.enemy_y - 25, self.enemy_hp, 100, bar_width)
        
        if self.slime_damage_taken > 0 and self.enemy_hp > 0:
            draw_text(f"-{self.slime_damage_taken}", 24, enemy_center_x, self.enemy_y - 55, RED, center=True)
            
        # --- MENGGAMBAR UI EDITOR KANAN ---
        pygame.draw.rect(screen, (44, 62, 80), self.ui_rect)
        
        npc_dialog_rect = pygame.Rect(self.arena_width + 10, 20, 250, 110)
        pygame.draw.rect(screen, (236, 240, 241), npc_dialog_rect, 0, 5)
        pygame.draw.rect(screen, BLACK, npc_dialog_rect, 2, 5)
        
        draw_text("NPC Guru:", 18, self.arena_width + 20, 30, BLACK)
        draw_text("Ketik kode untuk", 14, self.arena_width + 20, 55, BLACK)
        draw_text("menyerang:", 14, self.arena_width + 20, 75, BLACK)
        draw_text(self.target_code, 16, self.arena_width + 20, 95, (39, 174, 96))
        
        editor_bg_rect = pygame.Rect(self.arena_width + 10, 140, 250, 300)
        pygame.draw.rect(screen, BLACK, editor_bg_rect)
        draw_text(self.input_text, 20, self.arena_width + 20, 150, WHITE)
        
        if not self.is_enemy_turn and not self.is_victory and pygame.time.get_ticks() % 1000 < 500:
             cursor_x = self.arena_width + 20 + len(self.input_text) * 10
             pygame.draw.line(screen, WHITE, (cursor_x, 150), (cursor_x, 170), 2)
             
        feedback_rect = pygame.Rect(self.arena_width + 10, 460, 250, 70)
        pygame.draw.rect(screen, WHITE, feedback_rect, 2, 5)
        warna_teks = RED if self.player_damage_taken > 0 else YELLOW
        draw_text(self.feedback_text, 16, self.arena_width + 20, 480, warna_teks)
        
        draw_text("ESC: Peta | ENTER: Run", 14, self.arena_width + 135, SCREEN_HEIGHT - 30, WHITE, center=True)

        # ==========================================
        # MENGGAMBAR JENDELA KEMENANGAN
        # ==========================================
        if self.is_victory:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT)) 
            overlay.set_alpha(150) 
            overlay.fill(BLACK)    
            screen.blit(overlay, (0, 0)) 
            
            popup_rect = pygame.Rect(150, 200, 500, 200) 
            pygame.draw.rect(screen, WOOD_COLOR, popup_rect, border_radius=15)
            pygame.draw.rect(screen, BLACK, popup_rect, 5, border_radius=15)
            
            draw_text("KEMENANGAN!", 40, SCREEN_WIDTH // 2, 230, WHITE, center=True)
            draw_text("Selamat! Anda telah mengalahkan monster.", 20, SCREEN_WIDTH // 2, 280, BLACK, center=True)
            draw_text(f"Mendapatkan: {self.xp_reward} XP dan {self.gold_reward} Gold", 22, SCREEN_WIDTH // 2, 315, YELLOW, center=True)
            draw_text("Tekan ENTER untuk kembali ke Peta", 16, SCREEN_WIDTH // 2, 360, WHITE, center=True)

# ==========================================
#                GAME LOOP
# ==========================================
menu_scene = MainMenu()
world_map_scene = WorldMap()
combat_scene = CombatScene()

running = True
while running:
    events = pygame.event.get()
    for event in events:
        if event.type == pygame.QUIT:
            running = False

    if current_state == STATE_MENU:
        menu_scene.update(events)
    elif current_state == STATE_MAP:
        world_map_scene.update(events)
    elif current_state == STATE_COMBAT:
        combat_scene.update(events)

    screen.fill(BLACK) 
    
    if current_state == STATE_MENU:
        menu_scene.draw()
    elif current_state == STATE_MAP:
        world_map_scene.draw()
    elif current_state == STATE_COMBAT:
        combat_scene.draw()

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()