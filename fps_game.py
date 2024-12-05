from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QPointF, QRectF
from PyQt5.QtGui import QPainter, QColor, QKeyEvent, QRadialGradient, QPen, QFont, QPolygonF
import math
import random

class FPSGame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Player state
        self.player_x = 100
        self.player_y = 150
        self.player_angle = 0  # Looking angle in degrees
        self.player_health = 100
        self.ammo = 30
        self.score = 0
        self.kills = 0
        self.game_over = False
        
        # Movement
        self.keys_pressed = set()
        self.move_speed = 3
        self.turn_speed = 4
        self.mouse_sensitivity = 0.5
        self.recoil = 0
        
        # Weapon state
        self.is_shooting = False
        self.reload_timer = 0
        self.is_reloading = False
        self.shot_cooldown = 0
        self.muzzle_flash = 0
        
        # Map/Level
        self.walls = [
            # Outer walls
            [(20, 20), (180, 20)],
            [(180, 20), (180, 180)],
            [(180, 180), (20, 180)],
            [(20, 180), (20, 20)],
            # Inner obstacles
            [(60, 60), (140, 60)],
            [(100, 100), (140, 140)],
            [(60, 140), (100, 100)]
        ]
        
        # Enemies
        self.enemies = []
        self.spawn_enemies(3)  # Initial enemies
        
        # Effects
        self.particles = []  # [x, y, dx, dy, life, color]
        self.bullet_trails = []  # [start_x, start_y, end_x, end_y, life]
        self.blood_splats = []  # [x, y, size, alpha]
        
        # Colors
        self.wall_color = QColor("#455A64")
        self.enemy_color = QColor("#F44336")
        self.player_color = QColor("#4CAF50")
        self.bullet_color = QColor("#FFD700")
        
        # Game loop
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)  # 60 FPS
        
        # Capture mouse
        self.setMouseTracking(True)
        self.cursor_pos = self.rect().center()
        
    def spawn_enemies(self, count):
        """Spawn new enemies at random positions"""
        for _ in range(count):
            while True:
                x = random.randint(30, 170)
                y = random.randint(30, 170)
                # Check if position is valid (not too close to player or inside walls)
                if self.distance((x, y), (self.player_x, self.player_y)) > 50 and not self.point_collides_with_walls(x, y):
                    self.enemies.append({
                        'x': x,
                        'y': y,
                        'angle': random.uniform(0, 360),
                        'health': 100,
                        'state': 'patrol',  # patrol, chase, attack
                        'patrol_target': (x, y),
                        'last_shot': 0
                    })
                    break
    
    def distance(self, p1, p2):
        """Calculate distance between two points"""
        return math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
    
    def point_collides_with_walls(self, x, y, radius=5):
        """Check if a point collides with any walls"""
        for wall in self.walls:
            # Check distance to line segment
            x1, y1 = wall[0]
            x2, y2 = wall[1]
            
            # Vector math to find closest point on line
            line_vec = (x2-x1, y2-y1)
            point_vec = (x-x1, y-y1)
            line_len = self.distance(wall[0], wall[1])
            line_unitvec = (line_vec[0]/line_len, line_vec[1]/line_len)
            
            # Project point onto line
            point_proj_len = point_vec[0]*line_unitvec[0] + point_vec[1]*line_unitvec[1]
            point_proj_len = max(0, min(point_proj_len, line_len))
            
            # Find closest point
            closest_x = x1 + line_unitvec[0]*point_proj_len
            closest_y = y1 + line_unitvec[1]*point_proj_len
            
            if self.distance((x, y), (closest_x, closest_y)) < radius:
                return True
        return False
    
    def ray_wall_intersection(self, ray_start, ray_angle, max_dist=200):
        """Cast a ray and find intersection with walls"""
        ray_dir = (math.cos(math.radians(ray_angle)), math.sin(math.radians(ray_angle)))
        closest_hit = None
        closest_dist = max_dist
        
        for wall in self.walls:
            # Line segment intersection math
            x1, y1 = wall[0]
            x2, y2 = wall[1]
            x3, y3 = ray_start
            x4 = x3 + ray_dir[0]*max_dist
            y4 = y3 + ray_dir[1]*max_dist
            
            den = (x1-x2)*(y3-y4) - (y1-y2)*(x3-x4)
            if den == 0:
                continue
                
            t = ((x1-x3)*(y3-y4) - (y1-y3)*(x3-x4)) / den
            u = -((x1-x2)*(y1-y3) - (y1-y2)*(x1-x3)) / den
            
            if 0 <= t <= 1 and u >= 0:
                hit_x = x1 + t*(x2-x1)
                hit_y = y1 + t*(y2-y1)
                dist = self.distance(ray_start, (hit_x, hit_y))
                if dist < closest_dist:
                    closest_dist = dist
                    closest_hit = (hit_x, hit_y)
        
        return closest_hit, closest_dist
    
    def shoot(self):
        """Handle shooting logic"""
        if self.ammo <= 0 or self.is_reloading:
            return
            
        self.ammo -= 1
        self.shot_cooldown = 5
        self.muzzle_flash = 3
        
        # Add recoil
        self.recoil = min(self.recoil + 2, 10)
        
        # Calculate spread based on recoil
        spread = self.recoil * 2
        actual_angle = self.player_angle + random.uniform(-spread, spread)
        
        # Ray cast
        hit, dist = self.ray_wall_intersection(
            (self.player_x, self.player_y),
            actual_angle
        )
        
        if hit:
            # Add bullet trail
            self.bullet_trails.append([
                self.player_x, self.player_y,
                hit[0], hit[1],
                5  # Life in frames
            ])
            
            # Check enemy hits
            for enemy in self.enemies[:]:
                if self.distance((enemy['x'], enemy['y']), hit) < 10:
                    enemy['health'] -= random.randint(20, 35)
                    self.add_blood_particles(enemy['x'], enemy['y'])
                    if enemy['health'] <= 0:
                        self.enemies.remove(enemy)
                        self.score += 100
                        self.kills += 1
                        if len(self.enemies) < 3:
                            self.spawn_enemies(1)
    
    def reload(self):
        """Start reloading sequence"""
        if not self.is_reloading and self.ammo < 30:
            self.is_reloading = True
            self.reload_timer = 60  # 1 second
    
    def add_blood_particles(self, x, y):
        """Add blood particle effects"""
        for _ in range(8):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 3)
            self.particles.append([
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                30,  # Life
                QColor("#B71C1C")
            ])
        self.blood_splats.append([x, y, random.uniform(5, 10), 255])
    
    def update_game(self):
        if self.game_over:
            return
            
        # Update player movement
        dx = dy = 0
        if Qt.Key_W in self.keys_pressed:
            dx += math.cos(math.radians(self.player_angle)) * self.move_speed
            dy += math.sin(math.radians(self.player_angle)) * self.move_speed
        if Qt.Key_S in self.keys_pressed:
            dx -= math.cos(math.radians(self.player_angle)) * self.move_speed
            dy -= math.sin(math.radians(self.player_angle)) * self.move_speed
        if Qt.Key_A in self.keys_pressed:
            dx += math.cos(math.radians(self.player_angle - 90)) * self.move_speed
            dy += math.sin(math.radians(self.player_angle - 90)) * self.move_speed
        if Qt.Key_D in self.keys_pressed:
            dx += math.cos(math.radians(self.player_angle + 90)) * self.move_speed
            dy += math.sin(math.radians(self.player_angle + 90)) * self.move_speed
        
        # Test new position for collisions
        new_x = self.player_x + dx
        new_y = self.player_y + dy
        if not self.point_collides_with_walls(new_x, new_y, 10):
            self.player_x = new_x
            self.player_y = new_y
        
        # Update shooting
        if Qt.LeftButton in self.keys_pressed and self.shot_cooldown <= 0:
            self.shoot()
        
        # Update reloading
        if self.is_reloading:
            self.reload_timer -= 1
            if self.reload_timer <= 0:
                self.ammo = 30
                self.is_reloading = False
        
        # Update cooldowns
        if self.shot_cooldown > 0:
            self.shot_cooldown -= 1
        if self.muzzle_flash > 0:
            self.muzzle_flash -= 1
        if self.recoil > 0:
            self.recoil *= 0.9
        
        # Update enemies
        self.update_enemies()
        
        # Update particles
        self.update_particles()
        
        # Check game over
        if self.player_health <= 0:
            self.game_over = True
        
        self.update()
    
    def update_enemies(self):
        """Update enemy AI and movement"""
        for enemy in self.enemies:
            # Calculate distance to player
            dist_to_player = self.distance(
                (enemy['x'], enemy['y']),
                (self.player_x, self.player_y)
            )
            
            # Update enemy state
            if dist_to_player < 50:
                enemy['state'] = 'attack'
            elif dist_to_player < 100:
                enemy['state'] = 'chase'
            else:
                enemy['state'] = 'patrol'
            
            # Handle enemy behavior based on state
            if enemy['state'] == 'attack':
                # Face player
                dx = self.player_x - enemy['x']
                dy = self.player_y - enemy['y']
                enemy['angle'] = math.degrees(math.atan2(dy, dx))
                
                # Shoot at player
                if enemy['last_shot'] <= 0:
                    # Ray cast to check if player is visible
                    hit, _ = self.ray_wall_intersection(
                        (enemy['x'], enemy['y']),
                        enemy['angle']
                    )
                    if hit:
                        player_dist = self.distance(
                            (self.player_x, self.player_y),
                            hit
                        )
                        if player_dist < 10:
                            self.player_health -= random.randint(5, 10)
                            enemy['last_shot'] = 30  # Half second cooldown
            
            elif enemy['state'] == 'chase':
                # Move toward player
                angle = math.atan2(
                    self.player_y - enemy['y'],
                    self.player_x - enemy['x']
                )
                dx = math.cos(angle) * 1.5
                dy = math.sin(angle) * 1.5
                
                new_x = enemy['x'] + dx
                new_y = enemy['y'] + dy
                if not self.point_collides_with_walls(new_x, new_y):
                    enemy['x'] = new_x
                    enemy['y'] = new_y
            
            else:  # patrol
                # Move randomly
                if random.random() < 0.02:  # 2% chance to change direction
                    enemy['patrol_target'] = (
                        random.randint(30, 170),
                        random.randint(30, 170)
                    )
                
                dx = enemy['patrol_target'][0] - enemy['x']
                dy = enemy['patrol_target'][1] - enemy['y']
                dist = math.sqrt(dx*dx + dy*dy)
                
                if dist > 5:
                    enemy['x'] += (dx/dist)
                    enemy['y'] += (dy/dist)
            
            # Update cooldowns
            if enemy['last_shot'] > 0:
                enemy['last_shot'] -= 1
    
    def update_particles(self):
        """Update particle effects"""
        # Update particles
        for particle in self.particles[:]:
            particle[0] += particle[2]  # x += dx
            particle[1] += particle[3]  # y += dy
            particle[4] -= 1  # decrease lifetime
            if particle[4] <= 0:
                self.particles.remove(particle)
        
        # Update bullet trails
        for trail in self.bullet_trails[:]:
            trail[4] -= 1  # decrease lifetime
            if trail[4] <= 0:
                self.bullet_trails.remove(trail)
        
        # Update blood splats
        for splat in self.blood_splats[:]:
            splat[3] -= 0.5  # Fade out
            if splat[3] <= 0:
                self.blood_splats.remove(splat)
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_R:
            if self.game_over:
                self.restart_game()
            else:
                self.reload()
            return
            
        if self.game_over:
            return
            
        self.keys_pressed.add(event.key())
    
    def keyReleaseEvent(self, event: QKeyEvent):
        self.keys_pressed.discard(event.key())
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.keys_pressed.add(Qt.LeftButton)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.keys_pressed.discard(Qt.LeftButton)
    
    def mouseMoveEvent(self, event):
        if self.game_over:
            return
            
        # Calculate mouse movement from center
        center = self.rect().center()
        dx = event.pos().x() - center.x()
        
        # Update player angle
        self.player_angle += dx * self.mouse_sensitivity
        
        # Keep angle in [0, 360)
        self.player_angle %= 360
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw floor
        gradient = QRadialGradient(self.width()/2, self.height()/2, 
                                 max(self.width(), self.height()))
        gradient.setColorAt(0, QColor("#424242"))
        gradient.setColorAt(1, QColor("#212121"))
        painter.fillRect(0, 0, self.width(), self.height(), gradient)
        
        # Draw blood splats
        for splat in self.blood_splats:
            color = QColor("#B71C1C")
            color.setAlpha(int(splat[3]))
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(splat[0], splat[1]), splat[2], splat[2])
        
        # Draw walls
        painter.setPen(QPen(self.wall_color, 2))
        for wall in self.walls:
            painter.drawLine(wall[0][0], wall[0][1], wall[1][0], wall[1][1])
        
        # Draw bullet trails
        for trail in self.bullet_trails:
            color = self.bullet_color
            color.setAlpha(int((trail[4] / 5) * 255))
            painter.setPen(QPen(color, 1))
            painter.drawLine(trail[0], trail[1], trail[2], trail[3])
        
        # Draw particles
        for particle in self.particles:
            color = particle[5]
            color.setAlpha(int((particle[4] / 30) * 255))
            painter.setPen(QPen(color, 3))
            painter.drawPoint(int(particle[0]), int(particle[1]))
        
        # Draw enemies
        for enemy in self.enemies:
            # Enemy body
            painter.setBrush(self.enemy_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(enemy['x'], enemy['y']), 10, 10)
            
            # Enemy direction indicator
            angle_rad = math.radians(enemy['angle'])
            painter.drawLine(
                int(enemy['x']), int(enemy['y']),
                int(enemy['x'] + math.cos(angle_rad) * 15),
                int(enemy['y'] + math.sin(angle_rad) * 15)
            )
        
        # Draw player
        painter.save()
        painter.translate(self.player_x, self.player_y)
        painter.rotate(-self.player_angle)
        
        # Player body
        painter.setBrush(self.player_color)
        painter.setPen(Qt.NoPen)
        painter.drawRect(-8, -8, 16, 16)
        
        # Gun
        painter.setBrush(QColor("#666666"))
        painter.drawRect(8, -3, 12, 6)
        
        # Muzzle flash
        if self.muzzle_flash > 0:
            flash_gradient = QRadialGradient(20, 0, 10)
            flash_gradient.setColorAt(0, QColor(255, 200, 0, 200))
            flash_gradient.setColorAt(1, QColor(255, 100, 0, 0))
            painter.setBrush(flash_gradient)
            painter.drawEllipse(15, -5, 10, 10)
        
        painter.restore()
        
        # Draw HUD
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 8))
        
        # Health bar
        painter.fillRect(10, self.height()-40, 50, 5, QColor(50, 50, 50))
        health_color = QColor("#4CAF50") if self.player_health > 25 else QColor("#F44336")
        painter.fillRect(10, self.height()-40, int(self.player_health/2), 5, health_color)
        
        # Ammo counter
        painter.drawText(10, self.height()-15, f"Ammo: {self.ammo}/30")
        if self.is_reloading:
            painter.drawText(10, self.height()-5, "Reloading...")
        
        # Score
        painter.drawText(10, 20, f"Score: {self.score}")
        painter.drawText(10, 35, f"Kills: {self.kills}")
        
        # Crosshair
        if not self.game_over:
            painter.setPen(QPen(Qt.white, 1))
            size = 3 + self.recoil
            painter.drawLine(self.width()/2 - size, self.height()/2,
                           self.width()/2 + size, self.height()/2)
            painter.drawLine(self.width()/2, self.height()/2 - size,
                           self.width()/2, self.height()/2 + size)
        
        if self.game_over:
            painter.fillRect(0, 0, self.width(), self.height(), QColor(0, 0, 0, 150))
            painter.setPen(Qt.white)
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                f"Game Over!\nScore: {self.score}\nKills: {self.kills}\nPress R to restart"
            )
    
    def restart_game(self):
        """Reset the game state"""
        self.player_x = 100
        self.player_y = 150
        self.player_angle = 0
        self.player_health = 100
        self.ammo = 30
        self.score = 0
        self.kills = 0
        self.game_over = False
        self.is_reloading = False
        self.reload_timer = 0
        self.shot_cooldown = 0
        self.muzzle_flash = 0
        self.recoil = 0
        self.enemies.clear()
        self.particles.clear()
        self.bullet_trails.clear()
        self.blood_splats.clear()
        self.spawn_enemies(3)
        self.timer.start()
