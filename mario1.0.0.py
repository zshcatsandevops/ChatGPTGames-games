from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from panda3d.core import ClockObject
import random
import os

# ----------------------------------
# App setup & performance (60 FPS)
# ----------------------------------
app = Ursina()
window.title = 'CatOS 64: Shining Stars Repainted Ursina Mod'
window.vsync = True                      # sync to monitor (often 60Hz)
window.fps_counter.enabled = True        # on-screen FPS for debugging

# Hard cap at 60 FPS via Panda3D clock (reliable even on high-Hz monitors)
global_clock = ClockObject.getGlobalClock()
global_clock.setMode(ClockObject.MLimited)
global_clock.setFrameRate(60)

# ---------- GLOBALS ----------
stars_collected = 0
total_stars = 151
worlds = 15
stars = []
game_won = False

# ---------- WORLD ----------
ground = Entity(model='plane', scale=100, texture='grass', collider='box', color=color.green)

# Simple floating platforms (SM64-style hub scatter)
for i in range(20):
    Entity(model='cube',
           scale=(random.uniform(2, 5), 0.5, random.uniform(2, 5)),
           position=(random.uniform(-20, 20), random.uniform(0, 5), random.uniform(-20, 20)),
           color=random.choice([color.blue, color.red, color.yellow]),
           collider='box')

# ---------- STAR CREATION ----------
def create_stars():
    for i in range(total_stars):
        star = Entity(
            model='sphere',
            scale=0.5,
            color=color.yellow,
            position=(random.uniform(-30, 30), random.uniform(1, 10), random.uniform(-30, 30)),
            collider='sphere',
            rotation=(0, random.uniform(0, 360), 0)
        )
        stars.append(star)

create_stars()

# ---------- PLAYER ----------
player = FirstPersonController(model='cube', color=color.orange, scale=1, speed=8, jump_height=3)
player.cursor.visible = False

# ---------- LIGHTING ----------
directional_light = DirectionalLight()
directional_light.look_at(Vec3(1, -1, -1))
AmbientLight(color=color.rgba(120, 120, 120, 0.1))

# ---------- UI ----------
star_text = Text(f'Shining Stars Repainted\nStars: {stars_collected}/{total_stars}',
                 position=(-0.8, 0.45), scale=2, color=color.yellow)

# ---------- HELPERS ----------
def worlds_unlocked():
    return min(stars_collected // 10 + 1, worlds)

def update_ui():
    star_text.text = f'Shining Stars Repainted\nStars: {stars_collected}/{total_stars}'

# ---------- UPDATE ----------
def update():
    global stars_collected, game_won

    # Camera follow (third-person-ish)
    camera.position = lerp(camera.position, player.position + Vec3(0, 5, -10), time.dt * 5)
    camera.look_at(player)

    # Make stars gently spin for visibility
    for s in stars:
        s.rotation_y += 60 * time.dt

    # Star collection detection (simple distance check)
    for star in stars[:]:
        if distance(player.position, star.position) < 1.5:
            destroy(star)
            stars.remove(star)
            stars_collected += 1
            if os.path.exists('coin.mp3'):
                Audio('coin.mp3').play()
            else:
                print("⭐ Coin collected! (drop coin.mp3 next to program.py to enable sound)")
            print(f"Stars: {stars_collected}/{total_stars} | Worlds Unlocked: {worlds_unlocked()}")
            update_ui()

    # Win condition (show once)
    if not game_won and stars_collected >= total_stars:
        game_won = True
        banner = Text('Speedrun Complete!\nTime: 2:24:47 (Sim)', origin=(0, 0), scale=2, color=color.gold)
        banner.animate_position((0, 0), duration=2)

# ---------- INPUT ----------
def input(key):
    # Toggle wireframe safely (only for entities that support it)
    if key == 'f1':
        for e in scene.entities:
            if hasattr(e, 'wireframe'):
                e.wireframe = not getattr(e, 'wireframe', False)
        print("Wireframe mode toggled.")

    # Quit game
    if key == 'escape':
        quit()

# ---------- RUN ----------
if __name__ == "__main__":
    app.run()
