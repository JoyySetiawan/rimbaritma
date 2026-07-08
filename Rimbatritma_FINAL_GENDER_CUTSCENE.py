import pygame
import sys
import os
import math
import json

pygame.init()

# ==========================================
# AUDIO
# ==========================================
try:
    pygame.mixer.init()
except Exception:
    print("Audio mixer gagal dijalankan.")


# ==========================================
# KONFIGURASI LAYAR
# ==========================================
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Rimbaritma")

clock = pygame.time.Clock()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_DIR, "save_data.json")

# ==========================================
# WARNA
# ==========================================
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK = (18, 30, 47)
GREEN = (55, 190, 82)
RED = (226, 53, 53)
BLUE = (75, 145, 245)
YELLOW = (241, 196, 15)
GRAY = (149, 165, 166)
DARK_GREEN = (46, 204, 113)
PANEL_DARK = (44, 62, 80)
WOOD_COLOR = (205, 133, 63)
LOCKED_GRAY = (130, 130, 130)

# ==========================================
# STATE GAME
# ==========================================
STATE_MENU = "menu"
STATE_CUTSCENE = "cutscene"
STATE_MAP = "map"
STATE_COMBAT = "combat"

current_state = STATE_MENU
running = True

# ==========================================
# PROGRES GAME
# ==========================================
completed_levels = set()
highest_unlocked_level = 1


# ==========================================
# FUNGSI BANTUAN
# ==========================================
def asset_path(filename):
    candidates = [
        os.path.join(BASE_DIR, filename),

        os.path.join(BASE_DIR, "asset", filename),
        os.path.join(BASE_DIR, "asset", "images", filename),

        os.path.join(BASE_DIR, "assets", filename),
        os.path.join(BASE_DIR, "assets", "images", filename),

        os.path.join(BASE_DIR, "img", filename),
        os.path.join(BASE_DIR, "images", filename),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    return os.path.join(BASE_DIR, filename)


current_bgm = None


def play_bgm(filename, volume=0.55):
    global current_bgm

    if current_bgm == filename:
        return

    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.load(asset_path(filename))
        pygame.mixer.music.set_volume(volume)
        pygame.mixer.music.play(-1)
        current_bgm = filename
    except Exception:
        current_bgm = None
        print(f"Backsound tidak ditemukan atau gagal diputar: {filename}")


def stop_bgm():
    global current_bgm

    try:
        pygame.mixer.music.stop()
    except Exception:
        pass

    current_bgm = None


def draw_text(text, font_size, x, y, color=BLACK, center=False):
    font = pygame.font.SysFont("Arial", font_size, bold=True)
    text_surface = font.render(str(text), True, color)
    text_rect = text_surface.get_rect()

    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)

    screen.blit(text_surface, text_rect)


def draw_hp_bar(surface, x, y, hp, max_hp, width=140, height=16):
    if hp < 0:
        hp = 0

    if max_hp <= 0:
        max_hp = 1

    fill_width = int((hp / max_hp) * width)

    pygame.draw.rect(surface, RED, (x, y, width, height), border_radius=3)
    pygame.draw.rect(surface, DARK_GREEN, (x, y, fill_width, height), border_radius=3)
    pygame.draw.rect(surface, WHITE, (x, y, width, height), 2, border_radius=3)


def crop_transparent_or_uniform_border(image, tolerance=12):
    image = image.convert_alpha()
    width, height = image.get_size()

    corner_color = image.get_at((0, 0))
    corner_rgb = corner_color[:3]

    min_x = width
    min_y = height
    max_x = -1
    max_y = -1

    def is_border_pixel(pixel):
        r, g, b, a = pixel

        if a == 0:
            return True

        return (
            abs(r - corner_rgb[0]) <= tolerance and
            abs(g - corner_rgb[1]) <= tolerance and
            abs(b - corner_rgb[2]) <= tolerance
        )

    for y in range(height):
        for x in range(width):
            pixel = image.get_at((x, y))

            if not is_border_pixel(pixel):
                min_x = min(min_x, x)
                min_y = min(min_y, y)
                max_x = max(max_x, x)
                max_y = max(max_y, y)

    if max_x == -1 or max_y == -1:
        return image

    crop_width = max_x - min_x + 1
    crop_height = max_y - min_y + 1

    if crop_width < width * 0.3 or crop_height < height * 0.3:
        return image

    return image.subsurface((min_x, min_y, crop_width, crop_height)).copy()


def crop_by_alpha(image):
    image = image.convert_alpha()
    rect = image.get_bounding_rect(min_alpha=1)

    if rect.width == 0 or rect.height == 0:
        return image

    return image.subsurface(rect).copy()


def remove_uniform_background(image, tolerance=18):
    """
    Menghapus background warna polos dari gambar.
    Ini penting untuk asset gembok yang biasanya punya canvas hitam besar.
    Setelah background dihapus, gembok akan terlihat besar dan rapi saat ditempel di map.
    """
    image = image.convert_alpha()
    width, height = image.get_size()

    bg_color = image.get_at((0, 0))[:3]

    for y in range(height):
        for x in range(width):
            r, g, b, a = image.get_at((x, y))

            if (
                abs(r - bg_color[0]) <= tolerance
                and abs(g - bg_color[1]) <= tolerance
                and abs(b - bg_color[2]) <= tolerance
            ):
                image.set_at((x, y), (r, g, b, 0))

    rect = image.get_bounding_rect(min_alpha=1)

    if rect.width == 0 or rect.height == 0:
        return image

    return image.subsurface(rect).copy()


def cover_background(image, target_width, target_height):
    img_w, img_h = image.get_size()

    scale = max(target_width / img_w, target_height / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)

    scaled = pygame.transform.smoothscale(image, (new_w, new_h))

    crop_x = (new_w - target_width) // 2
    crop_y = (new_h - target_height) // 2

    return scaled.subsurface((crop_x, crop_y, target_width, target_height)).copy()


def load_scaled_sprite(filename, target_height):
    image = pygame.image.load(asset_path(filename)).convert_alpha()
    image = crop_by_alpha(image)

    original_width = image.get_width()
    original_height = image.get_height()

    ratio = target_height / original_height
    new_width = int(original_width * ratio)

    scaled = pygame.transform.smoothscale(image, (new_width, target_height))
    return scaled, new_width, target_height


def try_load_sprite(filename, target_height):
    try:
        return load_scaled_sprite(filename, target_height)
    except Exception:
        return None, 0, 0


def load_first_existing_sprite(filenames, target_height):
    for filename in filenames:
        try:
            return load_scaled_sprite(filename, target_height)
        except Exception:
            pass

    raise FileNotFoundError("Sprite tidak ditemukan")


def scale_cover_with_rect(image, target_width, target_height):
    img_w, img_h = image.get_size()

    scale = max(target_width / img_w, target_height / img_h)
    new_w = int(img_w * scale)
    new_h = int(img_h * scale)

    scaled = pygame.transform.smoothscale(image, (new_w, new_h))
    rect = scaled.get_rect(center=(target_width // 2, target_height // 2))

    return scaled, rect, scale


class Button:
    def __init__(self, rect, text, color, text_color=WHITE):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.color = color
        self.text_color = text_color

    def draw(self):
        mouse_pos = pygame.mouse.get_pos()

        draw_color = self.color
        if self.rect.collidepoint(mouse_pos):
            draw_color = (
                min(255, self.color[0] + 25),
                min(255, self.color[1] + 25),
                min(255, self.color[2] + 25),
            )

        pygame.draw.rect(screen, draw_color, self.rect, border_radius=12)
        pygame.draw.rect(screen, WHITE, self.rect, 2, border_radius=12)
        draw_text(self.text, 24, self.rect.centerx, self.rect.centery, self.text_color, center=True)

    def is_clicked(self, event):
        return (
            event.type == pygame.MOUSEBUTTONDOWN
            and event.button == 1
            and self.rect.collidepoint(event.pos)
        )


# ==========================================
# MAIN MENU
# ==========================================
class MainMenu:
    def __init__(self):
        # =====================================================
        # ANIMASI MENU UTAMA 14 FRAME
        # =====================================================
        # Simpan gambar menu utama dengan nama:
        # menu1.png sampai menu14.png
        #
        # Taruh di:
        # asset/
        # asset/images/
        # assets/
        # assets/images/

        self.menu_frames = []
        self.frame_index = 0
        self.frame_timer = 0
        self.frame_speed = 6

        for i in range(1, 15):
            candidates = [
                f"menu{i}.png",
                f"login{i}.png",
                f"main_menu{i}.png",
                f"mainmenu{i}.png",
                f"rimbamenu{i}.png",
                f"rimba_menu{i}.png",
                f"halaman_login{i}.png",
                f"halaman_menu{i}.png",
            ]

            loaded_frame = None

            for filename in candidates:
                try:
                    loaded_frame = pygame.image.load(asset_path(filename)).convert()
                    break
                except Exception:
                    loaded_frame = None

            if loaded_frame is not None:
                self.menu_frames.append(loaded_frame)

        if len(self.menu_frames) == 0:
            static_candidates = [
                "menu.png",
                "login.png",
                "main_menu.png",
                "mainmenu.png",
                "rimbamenu.png",
                "rimba_menu.png",
                "halaman_login.png",
                "halaman_menu.png",
            ]

            for filename in static_candidates:
                try:
                    frame = pygame.image.load(asset_path(filename)).convert()
                    self.menu_frames.append(frame)
                    break
                except Exception:
                    pass

        # =====================================================
        # GAMBAR POPUP NEW PLAYER DAN LOAD PLAYER
        # =====================================================
        # Rename gambar popup:
        # new_player.png  -> tampilan new player dengan pilihan gender
        # load_player.png -> tampilan load player
        #
        # Taruh di folder asset/ atau asset/images/.

        self.new_player_image = self.load_popup_image([
            "new_player.png",
            "newplayer.png",
            "popup_new.png",
            "menu_new_player.png",
            "new_player_menu.png",
        ])

        self.load_player_image = self.load_popup_image([
            "load_player.png",
            "loadplayer.png",
            "popup_load.png",
            "menu_load_player.png",
            "load_player_menu.png",
        ])

        # Mode:
        # main = menu utama NEW / LOAD
        # new = form new player
        # load = form load player
        self.mode = "main"

        # Hitbox tombol utama di gambar menu utama.
        # Tekan F1 untuk melihat kotak hitbox jika perlu kalibrasi.
        self.btn_new_rect = pygame.Rect(380, 535, 270, 145)
        self.btn_load_rect = pygame.Rect(670, 535, 285, 145)

        # Koordinat didasarkan pada desain gambar 1648 x 928.
        # Code akan otomatis menyesuaikan ke window 1280 x 720.
        self.popup_base_w = 1648
        self.popup_base_h = 928

        # Form NEW PLAYER terbaru dengan pilihan gender.
        self.new_nickname_base_rect = pygame.Rect(660, 350, 430, 62)
        self.new_password_base_rect = pygame.Rect(660, 477, 430, 62)
        self.male_base_rect = pygame.Rect(545, 595, 270, 90)
        self.female_base_rect = pygame.Rect(835, 595, 270, 90)
        self.new_confirm_base_rect = pygame.Rect(590, 730, 230, 72)
        self.new_back_base_rect = pygame.Rect(850, 730, 230, 72)

        # Form LOAD PLAYER.
        self.load_nickname_base_rect = pygame.Rect(660, 350, 430, 62)
        self.load_password_base_rect = pygame.Rect(660, 477, 430, 62)
        self.load_confirm_base_rect = pygame.Rect(590, 598, 230, 72)
        self.load_back_base_rect = pygame.Rect(850, 598, 230, 72)

        self.nickname_text = ""
        self.password_text = ""
        self.active_input = "nickname"

        # Default sementara laki-laki.
        # Nanti kalau mau, bisa dibuat tidak ada default dan user wajib pilih.
        self.selected_gender = "male"

        self.message_text = ""
        self.message_timer = 0

        self.show_hitbox = False

    def load_popup_image(self, filenames):
        for filename in filenames:
            try:
                return pygame.image.load(asset_path(filename)).convert()
            except Exception:
                pass

        return None

    def update_animation(self):
        if len(self.menu_frames) <= 1:
            return

        self.frame_timer += 1

        if self.frame_timer >= self.frame_speed:
            self.frame_timer = 0
            self.frame_index += 1

            if self.frame_index >= len(self.menu_frames):
                self.frame_index = 0

    def get_scaled_rect_from_base(self, base_rect, image=None):
        if image is not None:
            img_w, img_h = image.get_size()
        else:
            img_w, img_h = self.popup_base_w, self.popup_base_h

        scale = max(SCREEN_WIDTH / img_w, SCREEN_HEIGHT / img_h)
        scaled_w = int(img_w * scale)
        scaled_h = int(img_h * scale)

        offset_x = (SCREEN_WIDTH - scaled_w) // 2
        offset_y = (SCREEN_HEIGHT - scaled_h) // 2

        return pygame.Rect(
            int(offset_x + base_rect.x * scale),
            int(offset_y + base_rect.y * scale),
            int(base_rect.width * scale),
            int(base_rect.height * scale)
        )

    def get_current_popup_image(self):
        if self.mode == "new":
            return self.new_player_image

        if self.mode == "load":
            return self.load_player_image

        return None

    def get_popup_hitboxes(self):
        popup_image = self.get_current_popup_image()

        if self.mode == "new":
            nickname_rect = self.get_scaled_rect_from_base(self.new_nickname_base_rect, popup_image)
            password_rect = self.get_scaled_rect_from_base(self.new_password_base_rect, popup_image)
            male_rect = self.get_scaled_rect_from_base(self.male_base_rect, popup_image)
            female_rect = self.get_scaled_rect_from_base(self.female_base_rect, popup_image)
            confirm_rect = self.get_scaled_rect_from_base(self.new_confirm_base_rect, popup_image)
            back_rect = self.get_scaled_rect_from_base(self.new_back_base_rect, popup_image)
            return nickname_rect, password_rect, male_rect, female_rect, confirm_rect, back_rect

        nickname_rect = self.get_scaled_rect_from_base(self.load_nickname_base_rect, popup_image)
        password_rect = self.get_scaled_rect_from_base(self.load_password_base_rect, popup_image)
        confirm_rect = self.get_scaled_rect_from_base(self.load_confirm_base_rect, popup_image)
        back_rect = self.get_scaled_rect_from_base(self.load_back_base_rect, popup_image)

        return nickname_rect, password_rect, None, None, confirm_rect, back_rect

    def reset_form(self):
        self.nickname_text = ""
        self.password_text = ""
        self.active_input = "nickname"
        self.selected_gender = "male"
        self.message_text = ""
        self.message_timer = 0

    def start_new_game(self):
        global current_state, completed_levels, highest_unlocked_level

        nickname = self.nickname_text.strip()
        password = self.password_text.strip()

        if nickname == "" or password == "":
            self.message_text = "Nickname dan password wajib diisi."
            self.message_timer = 180
            return

        completed_levels = set()
        highest_unlocked_level = 1

        self.save_game_data(nickname, password, self.selected_gender)

        # Setelah akun baru dibuat, tampilkan cutscene sesuai gender.
        cutscene_scene.start(self.selected_gender)
        current_state = STATE_CUTSCENE

    def load_game(self):
        global current_state, completed_levels, highest_unlocked_level

        nickname = self.nickname_text.strip()
        password = self.password_text.strip()

        if nickname == "" or password == "":
            self.message_text = "Nickname dan password wajib diisi."
            self.message_timer = 180
            return

        if not os.path.exists(SAVE_FILE):
            self.message_text = "Data save belum ada."
            self.message_timer = 180
            return

        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)

            saved_nickname = data.get("nickname", "")
            saved_password = data.get("password", "")

            if nickname != saved_nickname or password != saved_password:
                self.message_text = "Nickname atau password salah."
                self.message_timer = 180
                return

            completed_levels = set(data.get("completed_levels", []))
            highest_unlocked_level = int(data.get("highest_unlocked_level", 1))

            current_state = STATE_MAP

        except Exception:
            self.message_text = "Gagal membaca data save."
            self.message_timer = 180

    def save_game_data(self, nickname, password, gender):
        data = {
            "nickname": nickname,
            "password": password,
            "gender": gender,
            "completed_levels": list(completed_levels),
            "highest_unlocked_level": highest_unlocked_level,
        }

        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4)
        except Exception:
            pass

    def update(self, events):
        global running

        self.update_animation()

        if self.message_timer > 0:
            self.message_timer -= 1

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.mode == "main":
                        running = False
                    else:
                        self.mode = "main"
                        self.reset_form()

                elif event.key == pygame.K_F1:
                    self.show_hitbox = not self.show_hitbox

                elif self.mode == "main":
                    if event.key == pygame.K_RETURN:
                        self.mode = "new"
                        self.reset_form()

                elif self.mode in ["new", "load"]:
                    if event.key == pygame.K_TAB:
                        if self.active_input == "nickname":
                            self.active_input = "password"
                        else:
                            self.active_input = "nickname"

                    elif event.key == pygame.K_RETURN:
                        if self.mode == "new":
                            self.start_new_game()
                        elif self.mode == "load":
                            self.load_game()

                    elif event.key == pygame.K_BACKSPACE:
                        if self.active_input == "nickname":
                            self.nickname_text = self.nickname_text[:-1]
                        else:
                            self.password_text = self.password_text[:-1]

                    else:
                        if event.unicode and event.unicode.isprintable():
                            if self.active_input == "nickname":
                                if len(self.nickname_text) < 18:
                                    self.nickname_text += event.unicode
                            else:
                                if len(self.password_text) < 18:
                                    self.password_text += event.unicode

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos

                if self.mode == "main":
                    if self.btn_new_rect.collidepoint(mouse_pos):
                        self.mode = "new"
                        self.reset_form()

                    elif self.btn_load_rect.collidepoint(mouse_pos):
                        self.mode = "load"
                        self.reset_form()

                elif self.mode in ["new", "load"]:
                    nickname_rect, password_rect, male_rect, female_rect, confirm_rect, back_rect = self.get_popup_hitboxes()

                    if nickname_rect.collidepoint(mouse_pos):
                        self.active_input = "nickname"

                    elif password_rect.collidepoint(mouse_pos):
                        self.active_input = "password"

                    elif self.mode == "new" and male_rect is not None and male_rect.collidepoint(mouse_pos):
                        self.selected_gender = "male"

                    elif self.mode == "new" and female_rect is not None and female_rect.collidepoint(mouse_pos):
                        self.selected_gender = "female"

                    elif confirm_rect.collidepoint(mouse_pos):
                        if self.mode == "new":
                            self.start_new_game()
                        elif self.mode == "load":
                            self.load_game()

                    elif back_rect.collidepoint(mouse_pos):
                        self.mode = "main"
                        self.reset_form()

    def draw_animated_background(self):
        if len(self.menu_frames) > 0:
            frame = self.menu_frames[self.frame_index]
            scaled_frame, frame_rect, _ = scale_cover_with_rect(frame, SCREEN_WIDTH, SCREEN_HEIGHT)
            screen.blit(scaled_frame, frame_rect)
        else:
            screen.fill(DARK)
            draw_text("RIMBARITMA", 60, SCREEN_WIDTH // 2, 170, WHITE, center=True)
            draw_text("File menu1.png - menu14.png belum ditemukan", 24, SCREEN_WIDTH // 2, 250, WHITE, center=True)

            fallback_new = Button(
                pygame.Rect(SCREEN_WIDTH // 2 - 140, 315, 280, 62),
                "NEW",
                GREEN,
                WHITE
            )

            fallback_exit = Button(
                pygame.Rect(SCREEN_WIDTH // 2 - 140, 400, 280, 62),
                "KELUAR",
                RED,
                WHITE
            )

            fallback_new.draw()
            fallback_exit.draw()

    def draw_popup_background(self):
        popup_image = self.get_current_popup_image()

        if popup_image is not None:
            scaled_popup, popup_rect, _ = scale_cover_with_rect(popup_image, SCREEN_WIDTH, SCREEN_HEIGHT)
            screen.blit(scaled_popup, popup_rect)
        else:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            screen.blit(overlay, (0, 0))

            popup_rect = pygame.Rect(0, 0, 680, 450)
            popup_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

            pygame.draw.rect(screen, WOOD_COLOR, popup_rect, border_radius=20)
            pygame.draw.rect(screen, BLACK, popup_rect, 5, border_radius=20)

            title = "NEW PLAYER" if self.mode == "new" else "LOAD PLAYER"
            draw_text(title, 42, popup_rect.centerx, popup_rect.top + 55, WHITE, center=True)
            draw_text("NICKNAME", 24, popup_rect.left + 90, popup_rect.top + 115, BLACK)
            draw_text("PASSWORD", 24, popup_rect.left + 90, popup_rect.top + 205, BLACK)

    def draw_form_text(self):
        if self.mode not in ["new", "load"]:
            return

        nickname_rect, password_rect, male_rect, female_rect, confirm_rect, back_rect = self.get_popup_hitboxes()

        font = pygame.font.SysFont("Consolas", 26, bold=False)

        # Cover placeholder text jika user sudah mengetik atau input sedang aktif.
        if self.nickname_text != "" or self.active_input == "nickname":
            pygame.draw.rect(
                screen,
                (82, 45, 20),
                pygame.Rect(nickname_rect.x + 14, nickname_rect.y + 8, nickname_rect.width - 28, nickname_rect.height - 16),
                border_radius=6
            )

        if self.password_text != "" or self.active_input == "password":
            pygame.draw.rect(
                screen,
                (82, 45, 20),
                pygame.Rect(password_rect.x + 14, password_rect.y + 8, password_rect.width - 28, password_rect.height - 16),
                border_radius=6
            )

        nickname_surface = font.render(self.nickname_text, True, (245, 220, 170))
        password_surface = font.render("*" * len(self.password_text), True, (245, 220, 170))

        screen.blit(nickname_surface, (nickname_rect.x + 28, nickname_rect.y + 18))
        screen.blit(password_surface, (password_rect.x + 28, password_rect.y + 18))

        # Cursor berkedip.
        if pygame.time.get_ticks() % 1000 < 500:
            if self.active_input == "nickname":
                cursor_x = nickname_rect.x + 30 + nickname_surface.get_width()
                cursor_y = nickname_rect.y + 18
                pygame.draw.line(screen, (245, 220, 170), (cursor_x, cursor_y), (cursor_x, cursor_y + 30), 2)

            elif self.active_input == "password":
                cursor_x = password_rect.x + 30 + password_surface.get_width()
                cursor_y = password_rect.y + 18
                pygame.draw.line(screen, (245, 220, 170), (cursor_x, cursor_y), (cursor_x, cursor_y + 30), 2)

        # Highlight pilihan gender pada NEW PLAYER.
        if self.mode == "new" and male_rect is not None and female_rect is not None:
            if self.selected_gender == "male":
                pygame.draw.rect(screen, YELLOW, male_rect, 4, border_radius=8)
            elif self.selected_gender == "female":
                pygame.draw.rect(screen, YELLOW, female_rect, 4, border_radius=8)

        if self.message_timer > 0 and self.message_text != "":
            draw_text(
                self.message_text,
                22,
                SCREEN_WIDTH // 2,
                675,
                RED,
                center=True
            )

    def draw_hitbox_debug(self):
        if not self.show_hitbox:
            return

        if self.mode == "main":
            pygame.draw.rect(screen, (0, 255, 0), self.btn_new_rect, 3)
            pygame.draw.rect(screen, (255, 255, 0), self.btn_load_rect, 3)

            draw_text("NEW", 20, self.btn_new_rect.centerx, self.btn_new_rect.top - 18, GREEN, center=True)
            draw_text("LOAD", 20, self.btn_load_rect.centerx, self.btn_load_rect.top - 18, YELLOW, center=True)

        elif self.mode in ["new", "load"]:
            nickname_rect, password_rect, male_rect, female_rect, confirm_rect, back_rect = self.get_popup_hitboxes()

            pygame.draw.rect(screen, (0, 255, 0), nickname_rect, 3)
            pygame.draw.rect(screen, (0, 255, 255), password_rect, 3)
            pygame.draw.rect(screen, (0, 255, 0), confirm_rect, 3)
            pygame.draw.rect(screen, (255, 255, 0), back_rect, 3)

            if male_rect is not None:
                pygame.draw.rect(screen, (0, 150, 255), male_rect, 3)
            if female_rect is not None:
                pygame.draw.rect(screen, (255, 0, 255), female_rect, 3)

    def draw(self):
        self.draw_animated_background()

        if self.mode in ["new", "load"]:
            self.draw_popup_background()
            self.draw_form_text()

        self.draw_hitbox_debug()




# ==========================================
# MAP LEVEL
# ==========================================
class WorldMap:
    def __init__(self):
        self.levels = [
            {"id": 1, "pos": (307, 611), "name": "Level 1 - Hutan Awal"},
            {"id": 2, "pos": (470, 388), "name": "Level 2 - Gurun"},
            {"id": 3, "pos": (720, 252), "name": "Level 3 - Gunung Es"},
            {"id": 4, "pos": (1029, 346), "name": "Level 4 - Kerajaan Hutan"},
            {"id": 5, "pos": (1367, 615), "name": "Level 5 - Gunung Api"},
        ]

        self.node_radius = 75
        self.visual_node_radius = 30
        self.popup_active = False
        self.selected_level = None
        self.info_message = ""
        self.info_timer = 0

        self.popup_rect = pygame.Rect(0, 0, 540, 300)
        self.popup_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

        self.btn_masuk = pygame.Rect(0, 0, 200, 56)
        self.btn_keluar = pygame.Rect(0, 0, 200, 56)
        self.btn_close = pygame.Rect(0, 0, 38, 38)

        self.btn_masuk.center = (self.popup_rect.centerx - 115, self.popup_rect.bottom - 78)
        self.btn_keluar.center = (self.popup_rect.centerx + 115, self.popup_rect.bottom - 78)
        self.btn_close.center = (self.popup_rect.right - 34, self.popup_rect.top + 34)

        try:
            self.map_image = pygame.image.load(asset_path("map.png")).convert()
        except Exception:
            self.map_image = None

        self.scaled_map = None
        self.map_rect = None
        self.map_scale = 1

        if self.map_image is not None:
            self.scaled_map, self.map_rect, self.map_scale = scale_cover_with_rect(
                self.map_image,
                SCREEN_WIDTH,
                SCREEN_HEIGHT
            )

        # Icon gembok untuk level yang terkunci.
        # Nama file yang didukung:
        # gembok_level.png, lock.png, gembok.png, lock_level.png
        self.lock_icon = None
        lock_filenames = [
            "gembok_level.png",
            "lock.png",
            "gembok.png",
            "lock_level.png",
        ]

        for filename in lock_filenames:
            try:
                raw_lock = pygame.image.load(asset_path(filename)).convert_alpha()
                raw_lock = remove_uniform_background(raw_lock, tolerance=18)
                self.lock_icon = pygame.transform.smoothscale(raw_lock, (56, 56))
                break
            except Exception:
                self.lock_icon = None

    def map_to_screen(self, map_pos):
        if self.map_rect is None:
            return int(map_pos[0]), int(map_pos[1])

        x = self.map_rect.x + int(map_pos[0] * self.map_scale)
        y = self.map_rect.y + int(map_pos[1] * self.map_scale)
        return x, y

    def screen_to_map(self, screen_pos):
        if self.map_rect is None:
            return screen_pos

        mx = (screen_pos[0] - self.map_rect.x) / self.map_scale
        my = (screen_pos[1] - self.map_rect.y) / self.map_scale
        return mx, my

    def get_clicked_level(self, mouse_pos):
        mx, my = self.screen_to_map(mouse_pos)

        for level in self.levels:
            level_x, level_y = level["pos"]

            distance = math.sqrt((mx - level_x) ** 2 + (my - level_y) ** 2)

            if distance <= self.node_radius:
                return level

        return None

    def close_popup(self):
        self.popup_active = False
        self.selected_level = None

    def update(self, events):
        global current_state, highest_unlocked_level

        mouse_pos = pygame.mouse.get_pos()

        if self.info_timer > 0:
            self.info_timer -= 1

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.popup_active:
                        self.close_popup()
                    else:
                        current_state = STATE_MENU

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.popup_active:
                    if self.btn_masuk.collidepoint(mouse_pos):
                        if self.selected_level is not None:
                            combat_scene.start_level(self.selected_level)

                        self.popup_active = False
                        current_state = STATE_COMBAT

                    elif self.btn_keluar.collidepoint(mouse_pos):
                        self.close_popup()

                    elif self.btn_close.collidepoint(mouse_pos):
                        self.close_popup()

                    elif not self.popup_rect.collidepoint(mouse_pos):
                        self.close_popup()

                    return

                clicked_level = self.get_clicked_level(mouse_pos)

                if clicked_level is not None:
                    if clicked_level["id"] <= highest_unlocked_level:
                        self.selected_level = clicked_level
                        self.popup_active = True
                    else:
                        self.info_message = "Level terkunci. Menangkan level sebelumnya dulu."
                        self.info_timer = 180

    def draw_hint(self):
        hint_rect = pygame.Rect(20, 18, 470, 48)
        hint_surface = pygame.Surface((hint_rect.width, hint_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(hint_surface, (0, 0, 0, 135), hint_surface.get_rect(), border_radius=12)
        screen.blit(hint_surface, hint_rect)

        draw_text("Klik lingkaran level untuk memilih stage", 22, 38, 30, WHITE)

        esc_rect = pygame.Rect(SCREEN_WIDTH - 170, 18, 150, 48)
        esc_surface = pygame.Surface((esc_rect.width, esc_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(esc_surface, (0, 0, 0, 135), esc_surface.get_rect(), border_radius=12)
        screen.blit(esc_surface, esc_rect)

        draw_text("Esc: Menu", 20, esc_rect.centerx, esc_rect.centery, WHITE, center=True)

    def draw_level_markers(self):
        global completed_levels, highest_unlocked_level

        for level in self.levels:
            sx, sy = self.map_to_screen(level["pos"])
            level_id = level["id"]

            # Level yang sudah dimenangkan diberi tanda hijau.
            if level_id in completed_levels:
                pygame.draw.circle(screen, GREEN, (sx, sy), 34)
                pygame.draw.circle(screen, WHITE, (sx, sy), 34, 4)
                draw_text(str(level_id), 26, sx, sy, WHITE, center=True)

            # Level yang masih terkunci diberi gembok di tengah node.
            elif level_id > highest_unlocked_level:
                if self.lock_icon is not None:
                    lock_rect = self.lock_icon.get_rect(center=(sx, sy))
                    screen.blit(self.lock_icon, lock_rect)
                else:
                    pygame.draw.circle(screen, LOCKED_GRAY, (sx, sy), 24)
                    pygame.draw.circle(screen, BLACK, (sx, sy), 24, 3)
                    draw_text("X", 18, sx, sy, WHITE, center=True)

            # Level yang terbuka tapi belum selesai tidak digambar ulang.
            # Marker asli dari map.png dibiarkan terlihat supaya rapi.
            else:
                pass

    def draw_info_message(self):
        if self.info_timer <= 0 or self.info_message == "":
            return

        info_rect = pygame.Rect(20, SCREEN_HEIGHT - 85, 470, 48)
        info_surface = pygame.Surface((info_rect.width, info_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(info_surface, (0, 0, 0, 140), info_surface.get_rect(), border_radius=12)
        screen.blit(info_surface, info_rect)

        draw_text(self.info_message, 20, 34, SCREEN_HEIGHT - 72, WHITE)

    def draw_popup(self):
        if self.selected_level is None:
            return

        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        screen.blit(overlay, (0, 0))

        pygame.draw.rect(screen, (245, 248, 255), self.popup_rect, border_radius=22)
        pygame.draw.rect(screen, GREEN, self.popup_rect, 5, border_radius=22)

        pygame.draw.circle(screen, RED, self.btn_close.center, 18)
        draw_text("X", 20, self.btn_close.centerx, self.btn_close.centery, WHITE, center=True)

        level_id = self.selected_level["id"]
        level_name = self.selected_level["name"]

        draw_text(f"LEVEL {level_id}", 44, self.popup_rect.centerx, self.popup_rect.top + 65, DARK, center=True)
        draw_text(level_name, 26, self.popup_rect.centerx, self.popup_rect.top + 120, PANEL_DARK, center=True)
        draw_text("Apakah kamu ingin masuk ke level ini?", 23, self.popup_rect.centerx, self.popup_rect.top + 170, (80, 90, 105), center=True)

        masuk_button = Button(self.btn_masuk, "MASUK", GREEN, WHITE)
        keluar_button = Button(self.btn_keluar, "KELUAR", RED, WHITE)

        masuk_button.draw()
        keluar_button.draw()

    def draw(self):
        if self.scaled_map is not None:
            screen.blit(self.scaled_map, self.map_rect)
        else:
            screen.fill(BLUE)
            draw_text("map.png tidak ditemukan", 40, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, WHITE, center=True)

        self.draw_level_markers()
        self.draw_hint()
        self.draw_info_message()

        if self.popup_active:
            self.draw_popup()


# ==========================================
# COMBAT SCENE
# ==========================================
class CombatScene:
    def __init__(self):
        self.arena_width = 700
        self.arena_rect = pygame.Rect(0, 0, self.arena_width, SCREEN_HEIGHT)
        self.ui_rect = pygame.Rect(self.arena_width, 0, SCREEN_WIDTH - self.arena_width, SCREEN_HEIGHT)

        self.ground_y = 610
        self.current_level = {"id": 1, "name": "Level 1 - Hutan Awal"}

        try:
            bg_original = pygame.image.load(asset_path("combat_bg.png")).convert_alpha()
            bg_cropped = crop_transparent_or_uniform_border(bg_original, tolerance=14)
            self.arena_bg = cover_background(bg_cropped, self.arena_width, SCREEN_HEIGHT)
            self.bg_loaded = True
        except Exception:
            self.bg_loaded = False

        # ==========================================
        # SPRITE PLAYER
        # ==========================================
        self.player_idle_image, self.player_width, self.player_height = try_load_sprite("kesatria_idle.png", 170)

        if self.player_idle_image is None:
            self.player_idle_image, self.player_width, self.player_height = try_load_sprite("kesatria.png", 170)

        self.image_loaded = self.player_idle_image is not None

        if not self.image_loaded:
            self.player_width = 90
            self.player_height = 170

        self.player_attack_frames = []

        for i in range(1, 6):
            frame, _, _ = try_load_sprite(f"kesatria_attack{i}.png", 170)
            if frame is not None:
                self.player_attack_frames.append(frame)

        self.player_attack_loaded = len(self.player_attack_frames) > 0

        self.stun_frames = []

        stun_file_groups = [
            ["kesatria_stun1.png", "kesatria_stun_1.png"],
            ["kesatria_stun2.png", "kesatria_stun_2.png"],
            ["kesatria_stun3.png", "kesatria_stun_3.png"],
        ]

        for group in stun_file_groups:
            try:
                stun_image, _, _ = load_first_existing_sprite(group, 170)
                self.stun_frames.append(stun_image)
            except Exception:
                pass

        self.stun_image_loaded = len(self.stun_frames) > 0
        self.stun_frame_index = 0
        self.stun_animation_timer = 0
        self.stun_animation_speed = 10

        # ==========================================
        # SPRITE MONSTER
        # ==========================================
        self.enemy_idle_image, self.enemy_width, self.enemy_height = try_load_sprite("monster_idle.png", 120)

        if self.enemy_idle_image is None:
            self.enemy_idle_image, self.enemy_width, self.enemy_height = try_load_sprite("monster_slime.png", 120)

        if self.enemy_idle_image is None:
            self.enemy_idle_image, self.enemy_width, self.enemy_height = try_load_sprite("monster_attack1.png", 120)

        self.enemy_image_loaded = self.enemy_idle_image is not None

        if not self.enemy_image_loaded:
            self.enemy_width = 120
            self.enemy_height = 120

        self.enemy_attack_frames = []

        for i in range(1, 5):
            frame, _, _ = try_load_sprite(f"monster_attack{i}.png", 120)
            if frame is not None:
                self.enemy_attack_frames.append(frame)

        self.enemy_attack_loaded = len(self.enemy_attack_frames) > 0

        # ==========================================
        # POSISI KARAKTER
        # ==========================================
        self.player_x = 120
        self.player_y = self.ground_y - self.player_height

        self.enemy_x = 430
        self.enemy_y = self.ground_y - self.enemy_height

        self.player_start_x = self.player_x
        self.enemy_start_x = self.enemy_x

        # ==========================================
        # STATUS GAMEPLAY
        # ==========================================
        self.player_max_hp = 100
        self.enemy_max_hp = 100
        self.player_hp = self.player_max_hp
        self.enemy_hp = self.enemy_max_hp

        self.slime_damage_taken = 0
        self.player_damage_taken = 0

        self.wrong_count = 0
        self.max_wrong_count = 3
        self.is_stunned = False

        self.input_text = ""
        self.target_code = 'print("Serang")'
        self.feedback_text = ""

        self.enemy_turn_delay = 0
        self.is_enemy_turn = False
        self.is_victory = False
        self.is_game_over = False

        self.xp_reward = 50
        self.gold_reward = 20

        # ==========================================
        # PROGRES MONSTER DALAM LEVEL
        # ==========================================
        self.total_monsters = 5
        self.current_monster_index = 1
        self.is_wave_transition = False
        self.wave_transition_delay = 0
        self.enemy_visible = True

        # ==========================================
        # STATUS ANIMASI ATTACK
        # ==========================================
        self.is_player_attacking = False
        self.player_attack_index = 0
        self.player_attack_timer = 0
        self.player_attack_speed = 6
        self.player_attack_damage_done = False
        self.pending_player_damage = 0

        self.is_enemy_attacking = False
        self.enemy_attack_index = 0
        self.enemy_attack_timer = 0
        self.enemy_attack_speed = 8
        self.enemy_attack_damage_done = False
        self.pending_enemy_damage = 0

    def start_level(self, level):
        self.current_level = level
        self.reset_combat()

        level_id = level["id"]

        self.enemy_max_hp = 100 + ((level_id - 1) * 25)
        self.enemy_hp = self.enemy_max_hp

        self.xp_reward = 50 + ((level_id - 1) * 20)
        self.gold_reward = 20 + ((level_id - 1) * 10)

        if level_id == 1:
            self.target_code = 'print("Serang")'
        elif level_id == 2:
            self.target_code = 'nama = "Rimba"'
        elif level_id == 3:
            self.target_code = 'angka = 10'
        elif level_id == 4:
            self.target_code = 'if True:'
        elif level_id == 5:
            self.target_code = 'class Hero:'

    def reset_combat(self):
        self.player_max_hp = 100
        self.player_hp = self.player_max_hp

        self.enemy_hp = self.enemy_max_hp

        self.is_victory = False
        self.is_game_over = False

        self.input_text = ""
        self.feedback_text = f"Monster 1 muncul!"

        self.slime_damage_taken = 0
        self.player_damage_taken = 0

        self.wrong_count = 0
        self.is_stunned = False

        self.stun_frame_index = 0
        self.stun_animation_timer = 0

        self.enemy_turn_delay = 0
        self.is_enemy_turn = False

        self.is_player_attacking = False
        self.player_attack_index = 0
        self.player_attack_timer = 0
        self.player_attack_damage_done = False
        self.pending_player_damage = 0

        self.is_enemy_attacking = False
        self.enemy_attack_index = 0
        self.enemy_attack_timer = 0
        self.enemy_attack_damage_done = False
        self.pending_enemy_damage = 0

        self.player_x = self.player_start_x
        self.enemy_x = self.enemy_start_x

        self.current_monster_index = 1
        self.is_wave_transition = False
        self.wave_transition_delay = 0
        self.enemy_visible = True

    def mark_level_completed(self):
        global completed_levels, highest_unlocked_level

        completed_levels.add(self.current_level["id"])

        if self.current_level["id"] >= highest_unlocked_level:
            highest_unlocked_level = min(5, self.current_level["id"] + 1)

    def update_stun_animation(self):
        if not self.is_stunned:
            self.stun_frame_index = 0
            self.stun_animation_timer = 0
            return

        if not self.stun_image_loaded:
            return

        self.stun_animation_timer += 1

        if self.stun_animation_timer >= self.stun_animation_speed:
            self.stun_animation_timer = 0
            self.stun_frame_index += 1

            if self.stun_frame_index >= len(self.stun_frames):
                self.stun_frame_index = 0

    def start_player_attack_animation(self, damage):
        self.is_player_attacking = True
        self.player_attack_index = 0
        self.player_attack_timer = 0
        self.player_attack_damage_done = False
        self.pending_player_damage = damage
        self.feedback_text = f"Menyerang monster {self.current_monster_index}!"

    def start_enemy_attack_animation(self, damage):
        self.is_enemy_attacking = True
        self.enemy_attack_index = 0
        self.enemy_attack_timer = 0
        self.enemy_attack_damage_done = False
        self.pending_enemy_damage = damage

        if self.is_stunned:
            self.feedback_text = "Player STUN! Musuh menyerang lagi!"
        else:
            self.feedback_text = f"Monster {self.current_monster_index} menyerang!"

    def update_player_attack_animation(self):
        if not self.is_player_attacking:
            return

        frame_count = len(self.player_attack_frames)

        if frame_count <= 0:
            self.apply_player_damage()
            self.finish_player_attack_animation()
            return

        self.player_attack_timer += 1

        if self.player_attack_index in [1, 2, 3]:
            self.player_x = self.player_start_x + 18
        else:
            self.player_x = self.player_start_x

        damage_frame = min(2, frame_count - 1)

        if self.player_attack_index >= damage_frame and not self.player_attack_damage_done:
            self.apply_player_damage()

        if self.player_attack_timer >= self.player_attack_speed:
            self.player_attack_timer = 0
            self.player_attack_index += 1

            if self.player_attack_index >= frame_count:
                self.finish_player_attack_animation()

    def apply_player_damage(self):
        if self.player_attack_damage_done:
            return

        self.enemy_hp -= self.pending_player_damage
        self.slime_damage_taken = self.pending_player_damage
        self.player_damage_taken = 0
        self.player_attack_damage_done = True

        if self.enemy_hp <= 0:
            self.enemy_hp = 0

    def prepare_next_monster(self):
        self.is_wave_transition = True
        self.wave_transition_delay = 55
        self.enemy_visible = False
        self.is_enemy_turn = False
        self.input_text = ""
        self.wrong_count = 0
        self.is_stunned = False
        self.feedback_text = f"Monster {self.current_monster_index} kalah! Monster {self.current_monster_index + 1} akan muncul."

    def spawn_next_monster(self):
        self.current_monster_index += 1
        self.enemy_hp = self.enemy_max_hp
        self.slime_damage_taken = 0
        self.player_damage_taken = 0
        self.enemy_visible = True
        self.is_wave_transition = False
        self.wave_transition_delay = 0
        self.feedback_text = f"Monster {self.current_monster_index} muncul!"

    def finish_player_attack_animation(self):
        self.is_player_attacking = False
        self.player_attack_index = 0
        self.player_attack_timer = 0
        self.player_x = self.player_start_x

        if self.enemy_hp <= 0:
            if self.current_monster_index < self.total_monsters:
                self.prepare_next_monster()
            else:
                self.mark_level_completed()
                self.is_victory = True
                self.feedback_text = "Semua monster kalah! Tekan ENTER."
        else:
            self.feedback_text = "Serangan berhasil!"
            self.is_enemy_turn = True
            self.enemy_turn_delay = 40

    def update_enemy_attack_animation(self):
        if not self.is_enemy_attacking:
            return

        frame_count = len(self.enemy_attack_frames)

        if frame_count <= 0:
            self.apply_enemy_damage()
            self.finish_enemy_attack_animation()
            return

        self.enemy_attack_timer += 1

        if self.enemy_attack_index in [1, 2]:
            self.enemy_x = self.enemy_start_x - 28
        else:
            self.enemy_x = self.enemy_start_x

        damage_frame = min(2, frame_count - 1)

        if self.enemy_attack_index >= damage_frame and not self.enemy_attack_damage_done:
            self.apply_enemy_damage()

        if self.enemy_attack_timer >= self.enemy_attack_speed:
            self.enemy_attack_timer = 0
            self.enemy_attack_index += 1

            if self.enemy_attack_index >= frame_count:
                self.finish_enemy_attack_animation()

    def apply_enemy_damage(self):
        if self.enemy_attack_damage_done:
            return

        self.player_hp -= self.pending_enemy_damage
        self.player_damage_taken = self.pending_enemy_damage
        self.slime_damage_taken = 0
        self.enemy_attack_damage_done = True

        if self.player_hp <= 0:
            self.player_hp = 0

    def finish_enemy_attack_animation(self):
        self.is_enemy_attacking = False
        self.enemy_attack_index = 0
        self.enemy_attack_timer = 0
        self.enemy_x = self.enemy_start_x

        if self.player_hp <= 0:
            self.is_game_over = True
            self.feedback_text = "Kalah! Tekan ENTER."
        else:
            if self.is_stunned:
                self.feedback_text = f"STUN selesai! Musuh memberi {self.pending_enemy_damage} DMG."
            else:
                self.feedback_text = f"Terkena {self.pending_enemy_damage} DMG!"

        self.is_stunned = False
        self.is_enemy_turn = False
        self.pending_enemy_damage = 0

    def update(self, events):
        global current_state

        self.update_stun_animation()

        if self.is_wave_transition:
            if self.wave_transition_delay > 0:
                self.wave_transition_delay -= 1
            else:
                self.spawn_next_monster()
            return

        if self.is_player_attacking:
            self.update_player_attack_animation()
            return

        if self.is_enemy_attacking:
            self.update_enemy_attack_animation()
            return

        if self.is_victory:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        current_state = STATE_MAP
            return

        if self.is_game_over:
            for event in events:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
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
                        current_state = STATE_MAP

                    elif event.key == pygame.K_BACKSPACE:
                        self.input_text = self.input_text[:-1]

                    elif event.key == pygame.K_RETURN:
                        self.check_code()

                    else:
                        if event.unicode and event.unicode.isprintable() and len(self.input_text) < 40:
                            self.input_text += event.unicode

    def check_code(self):
        typed_code = self.input_text.strip()

        if typed_code == self.target_code:
            damage = 25
            self.input_text = ""

            self.wrong_count = 0
            self.is_stunned = False
            self.start_player_attack_animation(damage)
        else:
            self.wrong_count += 1
            self.slime_damage_taken = 0
            self.player_damage_taken = 0
            self.input_text = ""

            if self.wrong_count >= self.max_wrong_count:
                self.wrong_count = 0
                self.is_stunned = True
                self.stun_frame_index = 0
                self.stun_animation_timer = 0
                self.feedback_text = "STUN! Salah 3 kali. Musuh menyerang lagi!"
            else:
                self.feedback_text = f"Kode salah! Kesalahan {self.wrong_count}/{self.max_wrong_count}"

            self.is_enemy_turn = True
            self.enemy_turn_delay = 40

    def musuh_menyerang(self):
        damage_musuh = 10 + ((self.current_level["id"] - 1) * 3)
        self.start_enemy_attack_animation(damage_musuh)

    def draw_arena_background(self):
        if self.bg_loaded:
            screen.blit(self.arena_bg, (0, 0))
        else:
            pygame.draw.rect(screen, GREEN, self.arena_rect)

        pygame.draw.rect(screen, BLACK, self.arena_rect, 4)

    def get_current_player_sprite(self):
        if self.is_player_attacking and self.player_attack_loaded:
            index = min(self.player_attack_index, len(self.player_attack_frames) - 1)
            return self.player_attack_frames[index]

        if self.is_stunned and self.stun_image_loaded:
            return self.stun_frames[self.stun_frame_index]

        if self.image_loaded:
            return self.player_idle_image

        return None

    def get_current_enemy_sprite(self):
        if self.is_enemy_attacking and self.enemy_attack_loaded:
            index = min(self.enemy_attack_index, len(self.enemy_attack_frames) - 1)
            return self.enemy_attack_frames[index]

        if self.enemy_image_loaded:
            return self.enemy_idle_image

        return None

    def draw_wave_progress(self):
        start_x = 130
        end_x = 540
        y = 72
        total = self.total_monsters

        if total > 1:
            pygame.draw.line(screen, BLACK, (start_x, y), (end_x, y), 3)

        spacing = 0
        if total > 1:
            spacing = (end_x - start_x) // (total - 1)

        for i in range(1, total + 1):
            x = start_x + (i - 1) * spacing

            if self.is_victory:
                fill = GREEN
                txt = WHITE
            elif i < self.current_monster_index:
                fill = GREEN
                txt = WHITE
            elif i == self.current_monster_index:
                fill = YELLOW
                txt = BLACK
            else:
                fill = BLACK
                txt = WHITE

            pygame.draw.circle(screen, fill, (x, y), 21)
            pygame.draw.circle(screen, WHITE, (x, y), 21, 2)
            draw_text(str(i), 18, x, y, txt, center=True)

    def draw_player(self):
        player_sprite = self.get_current_player_sprite()

        if player_sprite is not None:
            shake_x = 0
            if self.is_stunned:
                shake_x = -3 if (pygame.time.get_ticks() // 80) % 2 == 0 else 3

            screen.blit(player_sprite, (self.player_x + shake_x, self.player_y))
        else:
            fallback_color = RED if self.is_stunned else WHITE
            pygame.draw.rect(
                screen,
                fallback_color,
                pygame.Rect(self.player_x, self.player_y, self.player_width, self.player_height)
            )

        bar_width = 150
        bar_x = self.player_x + (self.player_width // 2) - (bar_width // 2)
        bar_y = self.player_y - 35

        draw_hp_bar(screen, bar_x, bar_y, self.player_hp, self.player_max_hp, bar_width, 18)

        if self.player_damage_taken > 0:
            draw_text(
                f"-{self.player_damage_taken}",
                28,
                self.player_x + (self.player_width // 2),
                self.player_y - 70,
                RED,
                center=True
            )

        if self.is_stunned:
            draw_text(
                "STUN",
                24,
                self.player_x + (self.player_width // 2),
                self.player_y - 95,
                RED,
                center=True
            )

    def draw_enemy(self):
        if not self.enemy_visible and not self.is_enemy_attacking:
            return

        enemy_sprite = self.get_current_enemy_sprite()

        if enemy_sprite is not None:
            screen.blit(enemy_sprite, (self.enemy_x, self.enemy_y))
        else:
            pygame.draw.circle(
                screen,
                BLUE,
                (self.enemy_x + (self.enemy_width // 2), self.enemy_y + (self.enemy_height // 2)),
                60
            )

        bar_width = 150
        bar_x = self.enemy_x + (self.enemy_width // 2) - (bar_width // 2)
        bar_y = self.enemy_y - 35

        draw_hp_bar(screen, bar_x, bar_y, self.enemy_hp, self.enemy_max_hp, bar_width, 18)

        if self.slime_damage_taken > 0 and self.enemy_hp > 0:
            draw_text(
                f"-{self.slime_damage_taken}",
                28,
                self.enemy_x + (self.enemy_width // 2),
                self.enemy_y - 70,
                RED,
                center=True
            )

    def draw_ui_panel(self):
        pygame.draw.rect(screen, PANEL_DARK, self.ui_rect)

        npc_dialog_rect = pygame.Rect(self.arena_width + 15, 25, SCREEN_WIDTH - self.arena_width - 30, 125)
        pygame.draw.rect(screen, (236, 240, 241), npc_dialog_rect, border_radius=6)
        pygame.draw.rect(screen, BLACK, npc_dialog_rect, 3, border_radius=6)

        draw_text("NPC Guru:", 22, self.arena_width + 30, 40, BLACK)
        draw_text("Ketik kode untuk", 18, self.arena_width + 30, 78, BLACK)
        draw_text("menyerang:", 18, self.arena_width + 30, 108, BLACK)
        draw_text(self.target_code, 18, self.arena_width + 30, 132, GREEN)

        if self.is_stunned:
            draw_text("STATUS: STUN", 18, self.arena_width + 245, 132, RED)
        else:
            draw_text(f"Salah: {self.wrong_count}/{self.max_wrong_count}", 18, self.arena_width + 245, 132, RED)

        editor_bg_rect = pygame.Rect(self.arena_width + 15, 165, SCREEN_WIDTH - self.arena_width - 30, 365)
        pygame.draw.rect(screen, BLACK, editor_bg_rect)
        pygame.draw.rect(screen, WHITE, editor_bg_rect, 2)

        draw_text(self.input_text, 28, self.arena_width + 28, 178, WHITE)

        if (
            not self.is_enemy_turn
            and not self.is_player_attacking
            and not self.is_enemy_attacking
            and not self.is_victory
            and not self.is_game_over
            and not self.is_wave_transition
        ):
            if pygame.time.get_ticks() % 1000 < 500:
                cursor_x = self.arena_width + 28 + len(self.input_text) * 14
                pygame.draw.line(screen, WHITE, (cursor_x, 180), (cursor_x, 210), 2)

        feedback_rect = pygame.Rect(self.arena_width + 15, 555, SCREEN_WIDTH - self.arena_width - 30, 85)
        pygame.draw.rect(screen, (52, 73, 94), feedback_rect, border_radius=4)
        pygame.draw.rect(screen, WHITE, feedback_rect, 2, border_radius=4)

        warna_teks = YELLOW
        if "Salah" in self.feedback_text or "salah" in self.feedback_text or "Kalah" in self.feedback_text:
            warna_teks = RED
        elif "STUN" in self.feedback_text:
            warna_teks = RED
        elif "Menang" in self.feedback_text or "muncul" in self.feedback_text or "berhasil" in self.feedback_text or "kalah!" in self.feedback_text:
            warna_teks = GREEN

        draw_text(self.feedback_text, 20, self.arena_width + 28, 585, warna_teks)

        draw_text(
            "ESC: Peta | ENTER: Run",
            18,
            self.arena_width + ((SCREEN_WIDTH - self.arena_width) // 2),
            SCREEN_HEIGHT - 28,
            WHITE,
            center=True
        )

    def draw_victory_popup(self):
        if self.is_victory:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(150)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))

            popup_rect = pygame.Rect(0, 0, 580, 250)
            popup_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

            pygame.draw.rect(screen, WOOD_COLOR, popup_rect, border_radius=15)
            pygame.draw.rect(screen, BLACK, popup_rect, 5, border_radius=15)

            draw_text("ANDA MENANG!", 42, SCREEN_WIDTH // 2, popup_rect.y + 45, WHITE, center=True)
            draw_text(
                f"Semua {self.total_monsters} monster pada level ini berhasil dikalahkan.",
                22,
                SCREEN_WIDTH // 2,
                popup_rect.y + 102,
                BLACK,
                center=True
            )
            draw_text(
                f"+{self.xp_reward} XP   +{self.gold_reward} Gold",
                24,
                SCREEN_WIDTH // 2,
                popup_rect.y + 145,
                YELLOW,
                center=True
            )
            draw_text(
                "Tekan ENTER untuk kembali ke peta",
                18,
                SCREEN_WIDTH // 2,
                popup_rect.y + 200,
                WHITE,
                center=True
            )

    def draw_game_over_popup(self):
        if self.is_game_over:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            overlay.set_alpha(150)
            overlay.fill(BLACK)
            screen.blit(overlay, (0, 0))

            popup_rect = pygame.Rect(0, 0, 520, 210)
            popup_rect.center = (SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)

            pygame.draw.rect(screen, RED, popup_rect, border_radius=15)
            pygame.draw.rect(screen, BLACK, popup_rect, 5, border_radius=15)

            draw_text("KALAH!", 40, SCREEN_WIDTH // 2, popup_rect.y + 50, WHITE, center=True)
            draw_text("Coba lagi dan perhatikan sintaks kode.", 22, SCREEN_WIDTH // 2, popup_rect.y + 110, BLACK, center=True)
            draw_text("Tekan ENTER untuk kembali ke peta", 18, SCREEN_WIDTH // 2, popup_rect.y + 160, WHITE, center=True)

    def draw(self):
        screen.fill(GRAY)

        self.draw_arena_background()
        self.draw_wave_progress()
        self.draw_player()
        self.draw_enemy()
        self.draw_ui_panel()
        self.draw_victory_popup()
        self.draw_game_over_popup()



# ==========================================
# CUTSCENE AWAL - VERSI LAKI-LAKI
# ==========================================
class CutsceneScene:
    def __init__(self):
        self.male_frames = self.load_cutscene_frames("laki")
        self.female_frames = self.load_cutscene_frames("perempuan")

        self.frames = self.male_frames
        self.gender = "male"
        self.current_index = 0

        self.dialogs = [
            [
                "Malam itu, seorang anak berusaha memahami sintaks Python.",
                "Namun semakin lama ia belajar, semakin besar rasa bingungnya."
            ],
            [
                '"Aduh... kenapa coding susah banget?"',
                '"Andai belajar coding bisa semudah bermain game..."'
            ],
            [
                "Tiba-tiba, layar komputer memancarkan cahaya misterius.",
                "Sebuah portal muncul dari dalam monitor."
            ],
            [
                '"Eh?! Apa itu?!"',
                "Sebelum sempat menghindar, portal itu menariknya masuk."
            ],
            [
                "Dalam sekejap, ia terlempar ke dunia asing bernama Rimba Ritma.",
                "Di dunia ini, kode bukan sekadar tulisan, tetapi sumber kekuatan."
            ],
            [
                "Seorang guru burung hantu berkacamata muncul di hadapannya.",
                '"Selamat datang di Rimba Ritma. Aku Guru Huma, pembimbingmu."'
            ],
            [
                '"Di dunia ini, kamu akan belajar coding sambil bertarung melawan monster."',
                '"Setiap sintaks yang benar akan berubah menjadi kekuatan."'
            ],
            [
                'Player terdiam sejenak, lalu menatap Guru Huma dengan penasaran.',
                '"Jadi... aku bisa belajar Python lewat petualangan ini?"'
            ],
            [
                '"Benar," jawab Guru Huma.',
                '"Aku akan menuntunmu langkah demi langkah sampai kamu memahaminya."'
            ],
            [
                '"Sekarang, bersiaplah untuk latihan pertamamu."',
                '"Petualanganmu di Rimba Ritma dimulai sekarang!"'
            ],
        ]

        self.dialog_line = 0
        self.fade_alpha = 255
        self.fade_speed = 12
        self.is_fading_in = True

    def load_cutscene_frames(self, prefix):
        frames = []

        for i in range(1, 11):
            filename = f"{prefix}{i}.png"

            try:
                image = pygame.image.load(asset_path(filename)).convert()
                frames.append(image)
            except Exception:
                pass

        return frames

    def start(self, gender="male"):
        self.gender = gender

        if gender == "female":
            if len(self.female_frames) > 0:
                self.frames = self.female_frames
            else:
                self.frames = self.male_frames
        else:
            self.frames = self.male_frames

        self.current_index = 0
        self.dialog_line = 0
        self.fade_alpha = 255
        self.is_fading_in = True

    def next_dialog(self):
        global current_state

        if len(self.frames) == 0:
            current_state = STATE_MAP
            return

        current_dialogs = self.dialogs[self.current_index]

        if self.dialog_line < len(current_dialogs) - 1:
            self.dialog_line += 1
        else:
            self.dialog_line = 0
            self.current_index += 1
            self.fade_alpha = 255
            self.is_fading_in = True

            if self.current_index >= len(self.frames):
                current_state = STATE_MAP

    def update(self, events):
        global current_state

        if self.is_fading_in:
            self.fade_alpha -= self.fade_speed

            if self.fade_alpha <= 0:
                self.fade_alpha = 0
                self.is_fading_in = False

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    self.next_dialog()

                elif event.key == pygame.K_ESCAPE:
                    current_state = STATE_MAP

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.next_dialog()

    def draw_dialog_box(self):
        if len(self.frames) == 0:
            return

        box_rect = pygame.Rect(90, SCREEN_HEIGHT - 150, SCREEN_WIDTH - 180, 105)

        dialog_surface = pygame.Surface((box_rect.width, box_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(dialog_surface, (0, 0, 0, 175), dialog_surface.get_rect(), border_radius=16)
        pygame.draw.rect(dialog_surface, WHITE, dialog_surface.get_rect(), 3, border_radius=16)
        screen.blit(dialog_surface, box_rect)

        current_dialogs = self.dialogs[self.current_index]
        text = current_dialogs[self.dialog_line]

        draw_text(text, 24, box_rect.x + 30, box_rect.y + 28, WHITE)

        if pygame.time.get_ticks() % 1000 < 600:
            draw_text("ENTER / klik untuk lanjut", 18, box_rect.right - 170, box_rect.bottom - 28, (220, 220, 220), center=True)

    def draw_scene_number(self):
        if len(self.frames) == 0:
            return

        text = f"{self.current_index + 1}/{len(self.frames)}"
        draw_text(text, 20, SCREEN_WIDTH - 60, 35, WHITE, center=True)

    def draw(self):
        if len(self.frames) > 0:
            image = self.frames[self.current_index]
            scaled_image, image_rect, _ = scale_cover_with_rect(image, SCREEN_WIDTH, SCREEN_HEIGHT)
            screen.blit(scaled_image, image_rect)
        else:
            screen.fill(DARK)
            draw_text("Cutscene belum ditemukan.", 28, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, WHITE, center=True)
            draw_text("Pastikan file laki1-laki10 atau perempuan1-perempuan10 ada di folder asset.", 20, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 42, WHITE, center=True)
            draw_text("Tekan ENTER untuk lanjut ke map", 22, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 84, WHITE, center=True)

        self.draw_dialog_box()
        self.draw_scene_number()

        if self.fade_alpha > 0:
            fade_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            fade_surface.set_alpha(self.fade_alpha)
            fade_surface.fill(BLACK)
            screen.blit(fade_surface, (0, 0))



# ==========================================
# OBJEK SCENE
# ==========================================
menu_scene = MainMenu()
cutscene_scene = CutsceneScene()
world_map_scene = WorldMap()
combat_scene = CombatScene()


# ==========================================
# GAME LOOP
# ==========================================
last_music_state = None

while running:
    events = pygame.event.get()

    for event in events:
        if event.type == pygame.QUIT:
            running = False

    if current_state == STATE_MENU:
        menu_scene.update(events)
    elif current_state == STATE_CUTSCENE:
        cutscene_scene.update(events)
    elif current_state == STATE_MAP:
        world_map_scene.update(events)
    elif current_state == STATE_COMBAT:
        combat_scene.update(events)

    # Backsound hanya untuk menu.
    # Pastikan file lagunya bernama menu_bgm.ogg
    # dan ditaruh di folder asset/ atau asset/images/.
    if current_state != last_music_state:
        if current_state == STATE_MENU:
            play_bgm("menu_bgm.ogg", 0.55)
        else:
            stop_bgm()

        last_music_state = current_state

    screen.fill(BLACK)

    if current_state == STATE_MENU:
        menu_scene.draw()
    elif current_state == STATE_CUTSCENE:
        cutscene_scene.draw()
    elif current_state == STATE_MAP:
        world_map_scene.draw()
    elif current_state == STATE_COMBAT:
        combat_scene.draw()

    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
sys.exit()
