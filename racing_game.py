from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QRect, QPointF
from PyQt5.QtGui import QPainter, QColor, QKeyEvent, QLinearGradient, QPen, QFont, QRadialGradient
import random
import math

class RacingGame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Track pressed keys
        self.keys_pressed = set()
        
        # Game state
        self.player_x = 100  # Center position
        self.player_y = 150  # Starting Y position
        self.player_speed = 0
        self.player_angle = 0  # Facing up (in degrees)
        self.score = 0
        self.distance = 0
        self.lap = 1
        self.game_over = False
        self.boost_fuel = 100
        self.is_boosting = False
        
        # Track
        self.track_points = self.generate_track()
        self.track_width = 40
        self.checkpoints = self.generate_checkpoints()
        self.next_checkpoint = 0
        
        # Obstacles and powerups
        self.obstacles = []  # [x, y, type]
        self.powerups = []   # [x, y, type]
        self.spawn_timer = 0
        
        # Physics
        self.acceleration = 0.2
        self.max_speed = 5
        self.friction = 0.98
        self.turn_speed = 5
        
        # Particles
        self.particles = []  # [x, y, dx, dy, life, color]
        self.skid_marks = []  # [x, y, angle, alpha]
        
        # Colors
        self.car_color = QColor("#4CAF50")
        self.track_color = QColor("#333333")
        self.grass_color = QColor("#1B5E20")
        self.boost_color = QColor("#FF9800")
        
        # Timer setup
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)  # 60 FPS
        
        # Initialize first obstacles
        self.spawn_obstacles()
    
    def generate_track(self):
        """Generate a procedural race track"""
        points = []
        center_x = self.width() / 2
        center_y = self.height() / 2
        radius = min(self.width(), self.height()) / 3
        
        # Generate a roughly circular track with some variation
        num_points = 12
        for i in range(num_points):
            angle = (i * 2 * math.pi) / num_points
            variation = random.uniform(0.8, 1.2)
            x = center_x + math.cos(angle) * radius * variation
            y = center_y + math.sin(angle) * radius * variation
            points.append(QPointF(x, y))
        
        return points
    
    def generate_checkpoints(self):
        """Generate checkpoints along the track"""
        checkpoints = []
        for i in range(len(self.track_points)):
            p1 = self.track_points[i]
            p2 = self.track_points[(i + 1) % len(self.track_points)]
            mid_x = (p1.x() + p2.x()) / 2
            mid_y = (p1.y() + p2.y()) / 2
            checkpoints.append(QPointF(mid_x, mid_y))
        return checkpoints
    
    def spawn_obstacles(self):
        """Spawn new obstacles and powerups"""
        if random.random() < 0.3:  # 30% chance to spawn
            track_idx = random.randint(0, len(self.track_points) - 1)
            p1 = self.track_points[track_idx]
            p2 = self.track_points[(track_idx + 1) % len(self.track_points)]
            
            # Random position along track segment
            t = random.random()
            x = p1.x() + (p2.x() - p1.x()) * t
            y = p1.y() + (p2.y() - p1.y()) * t
            
            if random.random() < 0.7:  # 70% obstacle, 30% powerup
                self.obstacles.append([x, y, random.choice(['oil', 'barrier'])])
            else:
                self.powerups.append([x, y, 'boost'])
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_R and self.game_over:
            self.restart_game()
            return
            
        if self.game_over:
            return
            
        self.keys_pressed.add(event.key())
        if event.key() == Qt.Key_Space and self.boost_fuel > 0:
            self.is_boosting = True
    
    def keyReleaseEvent(self, event: QKeyEvent):
        self.keys_pressed.discard(event.key())
        if event.key() == Qt.Key_Space:
            self.is_boosting = False
    
    def update_game(self):
        if self.game_over:
            return
        
        # Handle input
        if Qt.Key_Left in self.keys_pressed:
            self.player_angle += self.turn_speed
            self.add_skid_mark()
        if Qt.Key_Right in self.keys_pressed:
            self.player_angle -= self.turn_speed
            self.add_skid_mark()
        if Qt.Key_Up in self.keys_pressed:
            self.player_speed = min(self.player_speed + self.acceleration,
                                  self.max_speed * (1.5 if self.is_boosting else 1))
        if Qt.Key_Down in self.keys_pressed:
            self.player_speed = max(self.player_speed - self.acceleration, -self.max_speed/2)
        
        # Update boost
        if self.is_boosting and self.boost_fuel > 0:
            self.boost_fuel -= 1
            self.add_boost_particles()
        elif not self.is_boosting and self.boost_fuel < 100:
            self.boost_fuel += 0.2
        
        # Apply physics
        angle_rad = math.radians(self.player_angle)
        self.player_x += math.cos(angle_rad) * self.player_speed
        self.player_y -= math.sin(angle_rad) * self.player_speed
        self.player_speed *= self.friction
        
        # Keep player in bounds
        self.player_x = max(0, min(self.player_x, self.width()))
        self.player_y = max(0, min(self.player_y, self.height()))
        
        # Check collisions
        self.check_collisions()
        
        # Update particles
        self.update_particles()
        
        # Spawn new obstacles
        self.spawn_timer += 1
        if self.spawn_timer >= 60:  # Every second
            self.spawn_timer = 0
            self.spawn_obstacles()
        
        # Update score
        self.distance += abs(self.player_speed)
        if self.distance > self.lap * 1000:
            self.lap += 1
            self.score += 1000
        
        self.update()
    
    def check_collisions(self):
        """Check for collisions with obstacles and powerups"""
        player_rect = QRect(
            int(self.player_x - 10),
            int(self.player_y - 10),
            20, 20
        )
        
        # Check obstacles
        for obstacle in self.obstacles[:]:
            obstacle_rect = QRect(
                int(obstacle[0] - 15),
                int(obstacle[1] - 15),
                30, 30
            )
            if player_rect.intersects(obstacle_rect):
                if obstacle[2] == 'oil':
                    self.player_speed *= 0.5
                    self.player_angle += random.uniform(-30, 30)
                else:  # barrier
                    self.game_over = True
                self.obstacles.remove(obstacle)
                self.add_collision_particles(obstacle[0], obstacle[1])
        
        # Check powerups
        for powerup in self.powerups[:]:
            powerup_rect = QRect(
                int(powerup[0] - 10),
                int(powerup[1] - 10),
                20, 20
            )
            if player_rect.intersects(powerup_rect):
                if powerup[2] == 'boost':
                    self.boost_fuel = 100
                self.powerups.remove(powerup)
                self.add_collect_particles(powerup[0], powerup[1])
        
        # Check checkpoints
        checkpoint = self.checkpoints[self.next_checkpoint]
        cp_rect = QRect(
            int(checkpoint.x() - 20),
            int(checkpoint.y() - 20),
            40, 40
        )
        if player_rect.intersects(cp_rect):
            self.next_checkpoint = (self.next_checkpoint + 1) % len(self.checkpoints)
            self.score += 100
    
    def add_skid_mark(self):
        """Add skid marks when turning sharply"""
        if abs(self.player_speed) > 2:
            self.skid_marks.append([
                self.player_x,
                self.player_y,
                self.player_angle,
                255  # Initial alpha
            ])
    
    def add_boost_particles(self):
        """Add particles when boosting"""
        angle_rad = math.radians(self.player_angle + 180)  # Behind the car
        for _ in range(2):
            speed = random.uniform(2, 4)
            spread = random.uniform(-0.5, 0.5)
            self.particles.append([
                self.player_x,
                self.player_y,
                math.cos(angle_rad + spread) * speed,
                math.sin(angle_rad + spread) * speed,
                20,  # Life
                self.boost_color
            ])
    
    def add_collision_particles(self, x, y):
        """Add particles on collision"""
        for _ in range(10):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 5)
            self.particles.append([
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                30,  # Life
                QColor("#FF5252")
            ])
    
    def add_collect_particles(self, x, y):
        """Add particles when collecting powerups"""
        for _ in range(8):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 3)
            self.particles.append([
                x, y,
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                25,  # Life
                QColor("#FFD700")
            ])
    
    def update_particles(self):
        """Update particle positions and lifetimes"""
        for particle in self.particles[:]:
            particle[0] += particle[2]  # x += dx
            particle[1] += particle[3]  # y += dy
            particle[4] -= 1  # decrease lifetime
            if particle[4] <= 0:
                self.particles.remove(particle)
        
        # Update skid marks
        for mark in self.skid_marks[:]:
            mark[3] -= 2  # Fade out
            if mark[3] <= 0:
                self.skid_marks.remove(mark)
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw background (grass)
        gradient = QRadialGradient(self.width()/2, self.height()/2, 
                                 max(self.width(), self.height()))
        gradient.setColorAt(0, self.grass_color.lighter())
        gradient.setColorAt(1, self.grass_color)
        painter.fillRect(0, 0, self.width(), self.height(), gradient)
        
        # Draw track
        painter.setPen(QPen(self.track_color.darker(), self.track_width))
        path = painter.drawPolyline(self.track_points)
        
        # Draw skid marks
        for mark in self.skid_marks:
            painter.setPen(QPen(QColor(0, 0, 0, mark[3]), 2))
            painter.drawPoint(int(mark[0]), int(mark[1]))
        
        # Draw particles
        for particle in self.particles:
            color = particle[5]
            color.setAlpha(int((particle[4] / 30) * 255))
            painter.setPen(QPen(color, 3))
            painter.drawPoint(int(particle[0]), int(particle[1]))
        
        # Draw checkpoints
        checkpoint = self.checkpoints[self.next_checkpoint]
        painter.setPen(QPen(QColor("#FFD700"), 2))
        painter.drawEllipse(checkpoint, 10, 10)
        
        # Draw obstacles and powerups
        for obstacle in self.obstacles:
            if obstacle[2] == 'oil':
                color = QColor("#4A148C")
            else:
                color = QColor("#B71C1C")
            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QPointF(obstacle[0], obstacle[1]), 15, 15)
        
        for powerup in self.powerups:
            painter.setBrush(self.boost_color)
            painter.setPen(Qt.NoPen)
            painter.drawRect(int(powerup[0]-10), int(powerup[1]-10), 20, 20)
        
        # Draw player (car)
        painter.save()
        painter.translate(self.player_x, self.player_y)
        painter.rotate(-self.player_angle)
        
        # Car body
        painter.setBrush(self.car_color)
        painter.setPen(QPen(self.car_color.darker(), 1))
        painter.drawRect(-10, -15, 20, 30)
        
        # Boost flames
        if self.is_boosting and self.boost_fuel > 0:
            flame_gradient = QLinearGradient(0, 15, 0, 25)
            flame_gradient.setColorAt(0, QColor("#FF9800"))
            flame_gradient.setColorAt(1, QColor("#F44336"))
            painter.setBrush(flame_gradient)
            painter.setPen(Qt.NoPen)
            painter.drawRect(-8, 15, 16, 10)
        
        painter.restore()
        
        # Draw HUD
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 8))
        painter.drawText(10, 20, f"Score: {self.score}")
        painter.drawText(10, 35, f"Lap: {self.lap}")
        
        # Draw boost meter
        painter.fillRect(10, self.height()-20, 50, 10, QColor(50, 50, 50))
        painter.fillRect(10, self.height()-20, int(self.boost_fuel/2), 10, self.boost_color)
        
        if self.game_over:
            painter.fillRect(0, 0, self.width(), self.height(), QColor(0, 0, 0, 150))
            painter.setPen(Qt.white)
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                f"Game Over!\nScore: {self.score}\nLaps: {self.lap}\nPress R to restart"
            )
    
    def restart_game(self):
        """Reset the game state"""
        self.player_x = 100
        self.player_y = 150
        self.player_speed = 0
        self.player_angle = 0
        self.score = 0
        self.distance = 0
        self.lap = 1
        self.game_over = False
        self.boost_fuel = 100
        self.is_boosting = False
        self.obstacles.clear()
        self.powerups.clear()
        self.particles.clear()
        self.skid_marks.clear()
        self.next_checkpoint = 0
        self.spawn_timer = 0
        self.timer.start()
