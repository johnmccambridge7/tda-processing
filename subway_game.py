from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QRect, QPointF
from PyQt5.QtGui import QPainter, QColor, QKeyEvent, QLinearGradient, QPen, QFont
import random
import math

class SubwayGame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Game state
        self.player_lane = 1
        self.player_y = 150
        self.is_jumping = False
        self.is_rolling = False
        self.jump_height = 0
        self.roll_animation = 0
        self.score = 0
        self.coins = 0
        self.game_over = False
        self.level = 1
        self.distance = 0
        self.boost_mode = False
        self.boost_timer = 0
        
        # Player movement
        self.lane_change_speed = 5
        self.target_lane = 1
        self.current_lane_pos = 1
        
        # Obstacles and collectibles
        self.obstacles = []  # [lane, y_pos, type]
        self.coins_list = []  # [lane, y_pos]
        self.powerups = []  # [lane, y_pos, type]
        self.obstacle_speed = 3
        self.base_obstacle_speed = 3
        
        # Visual effects
        self.particles = []  # [x, y, dx, dy, life]
        self.background_offset = 0
        
        # Colors and styling
        self.player_color = QColor("#4CAF50")
        self.obstacle_colors = {
            'regular': QColor("#F44336"),
            'special': QColor("#FF9800"),
            'barrier': QColor("#9C27B0")
        }
        self.coin_color = QColor("#FFD700")
        self.powerup_colors = {
            'boost': QColor("#2196F3"),
            'magnet': QColor("#E91E63"),
            'shield': QColor("#00BCD4")
        }
        self.background_color = QColor("#2E2E2E")
        
        # Setup timers
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)
        
        self.spawn_timer = QTimer(self)
        self.spawn_timer.timeout.connect(self.spawn_objects)
        self.spawn_timer.start(1500)
        
        # Particle effects
        self.trail_particles = []
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw animated background
        self.draw_background(painter)
        
        # Draw lanes with perspective
        self.draw_lanes(painter)
        
        # Draw particles
        self.draw_particles(painter)
        
        # Draw coins
        lane_width = self.width() // 3
        for coin in self.coins_list:
            lane, y_pos = coin
            x = (lane * lane_width) + (lane_width // 4)
            self.draw_coin(painter, x, y_pos)
        
        # Draw powerups
        for powerup in self.powerups:
            lane, y_pos, p_type = powerup
            x = (lane * lane_width) + (lane_width // 4)
            self.draw_powerup(painter, x, y_pos, p_type)
        
        # Draw obstacles with different types
        for obstacle in self.obstacles:
            lane, y_pos, o_type = obstacle
            x = (lane * lane_width) + (lane_width // 4)
            self.draw_obstacle(painter, x, y_pos, o_type)
        
        # Draw player with animations
        player_x = self.get_interpolated_x()
        player_y = self.player_y - self.jump_height
        self.draw_player(painter, player_x, player_y)
        
        # Draw HUD
        self.draw_hud(painter)
        
        if self.game_over:
            self.draw_game_over(painter)
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_R and self.game_over:
            self.restart_game()
            return
            
        if self.game_over:
            return
            
        if event.key() == Qt.Key_Left and self.target_lane > 0:
            self.target_lane -= 1
        elif event.key() == Qt.Key_Right and self.target_lane < 2:
            self.target_lane += 1
        elif event.key() == Qt.Key_Space and not self.is_jumping and not self.is_rolling:
            self.is_jumping = True
            self.jump_height = 0
            self.add_jump_particles()
        elif event.key() == Qt.Key_Down and not self.is_jumping:
            self.is_rolling = True
            self.roll_animation = 0
    
    def update_game(self):
        if self.game_over:
            return
            
        # Update player movement
        self.update_player_position()
        
        # Update jump and roll animations
        self.update_player_animations()
        
        # Update game objects
        self.update_objects()
        
        # Update particles
        self.update_particles()
        
        # Update boost mode
        if self.boost_mode:
            self.boost_timer -= 1
            if self.boost_timer <= 0:
                self.boost_mode = False
                self.obstacle_speed = self.base_obstacle_speed
        
        # Increase difficulty over time
        self.distance += self.obstacle_speed
        if self.distance > self.level * 1000:
            self.level_up()
        
        self.update()
    
    def update_player_position(self):
        # Smooth lane changes
        if self.current_lane_pos != self.target_lane:
            diff = self.target_lane - self.current_lane_pos
            self.current_lane_pos += math.copysign(self.lane_change_speed * 0.1, diff)
            if abs(diff) < 0.1:
                self.current_lane_pos = self.target_lane
        
        # Add trail particles during movement
        if self.current_lane_pos != self.target_lane:
            self.add_trail_particles()
    
    def update_player_animations(self):
        # Jump animation
        if self.is_jumping:
            self.jump_height += 5
            if self.jump_height >= 50:
                self.is_jumping = False
        elif self.jump_height > 0:
            self.jump_height -= 5
        
        # Roll animation
        if self.is_rolling:
            self.roll_animation += 15
            if self.roll_animation >= 360:
                self.is_rolling = False
                self.roll_animation = 0
    
    def update_objects(self):
        lane_width = self.width() // 3
        player_x = self.get_interpolated_x()
        player_y = self.player_y - self.jump_height
        
        # Update and check coins
        for coin in self.coins_list[:]:
            coin[1] += self.obstacle_speed
            if coin[1] > self.height():
                self.coins_list.remove(coin)
            else:
                coin_rect = QRect(
                    (coin[0] * lane_width) + (lane_width // 4),
                    coin[1],
                    lane_width // 4,
                    lane_width // 4
                )
                player_rect = self.get_player_hitbox(player_x, player_y)
                if player_rect.intersects(coin_rect):
                    self.coins_list.remove(coin)
                    self.coins += 1
                    self.add_collect_particles(coin_rect.center())
        
        # Update and check powerups
        for powerup in self.powerups[:]:
            powerup[1] += self.obstacle_speed
            if powerup[1] > self.height():
                self.powerups.remove(powerup)
            else:
                powerup_rect = QRect(
                    (powerup[0] * lane_width) + (lane_width // 4),
                    powerup[1],
                    lane_width // 3,
                    lane_width // 3
                )
                player_rect = self.get_player_hitbox(player_x, player_y)
                if player_rect.intersects(powerup_rect):
                    self.activate_powerup(powerup[2])
                    self.powerups.remove(powerup)
        
        # Update and check obstacles
        for obstacle in self.obstacles[:]:
            obstacle[1] += self.obstacle_speed
            if obstacle[1] > self.height():
                self.obstacles.remove(obstacle)
                self.score += 1
            else:
                obstacle_rect = self.get_obstacle_hitbox(obstacle)
                player_rect = self.get_player_hitbox(player_x, player_y)
                
                if not self.boost_mode and player_rect.intersects(obstacle_rect):
                    if not self.is_rolling:  # Can roll under some obstacles
                        self.game_over = True
                        self.timer.stop()
                        self.spawn_timer.stop()
                        self.add_explosion_particles(player_rect.center())
    
    def update_particles(self):
        # Update particle positions and lifetimes
        for particle in self.particles[:]:
            particle[0] += particle[2]  # x += dx
            particle[1] += particle[3]  # y += dy
            particle[4] -= 1  # decrease lifetime
            if particle[4] <= 0:
                self.particles.remove(particle)
        
        # Update trail particles
        for particle in self.trail_particles[:]:
            particle[1] += self.obstacle_speed * 1.5
            particle[4] -= 1
            if particle[4] <= 0:
                self.trail_particles.remove(particle)
    
    def spawn_objects(self):
        if self.game_over:
            return
            
        # Spawn obstacles
        if random.random() < 0.7:  # 70% chance to spawn obstacle
            lane = random.randint(0, 2)
            obstacle_type = random.choice(['regular', 'special', 'barrier'])
            self.obstacles.append([lane, -20, obstacle_type])
        
        # Spawn coins
        if random.random() < 0.4:  # 40% chance to spawn coin
            lane = random.randint(0, 2)
            self.coins_list.append([lane, -20])
        
        # Spawn powerups
        if random.random() < 0.1:  # 10% chance to spawn powerup
            lane = random.randint(0, 2)
            powerup_type = random.choice(['boost', 'magnet', 'shield'])
            self.powerups.append([lane, -20, powerup_type])
    
    def get_interpolated_x(self):
        lane_width = self.width() // 3
        return (self.current_lane_pos * lane_width) + (lane_width // 4)
    
    def get_player_hitbox(self, x, y):
        if self.is_rolling:
            return QRect(int(x), int(y + 15), self.width() // 6, 15)
        return QRect(int(x), int(y), self.width() // 6, 30)
    
    def get_obstacle_hitbox(self, obstacle):
        lane_width = self.width() // 3
        return QRect(
            (obstacle[0] * lane_width) + (lane_width // 4),
            obstacle[1],
            lane_width // 2,
            20
        )
    
    def draw_background(self, painter):
        # Create gradient background
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#1a237e"))
        gradient.setColorAt(1, QColor("#303F9F"))
        painter.fillRect(0, 0, self.width(), self.height(), gradient)
        
        # Draw moving lines for speed effect
        self.background_offset = (self.background_offset + self.obstacle_speed) % 40
        painter.setPen(QPen(QColor("#3949AB"), 2, Qt.DashLine))
        for y in range(-40 + int(self.background_offset), self.height(), 40):
            painter.drawLine(0, y, self.width(), y)
    
    def draw_lanes(self, painter):
        lane_width = self.width() // 3
        for i in range(4):
            x = i * lane_width
            painter.setPen(QPen(QColor("#5C6BC0"), 2))
            painter.drawLine(x, 0, x, self.height())
    
    def draw_player(self, painter, x, y):
        if self.is_rolling:
            # Draw rolling animation
            painter.save()
            painter.translate(x + self.width() // 12, y + 22)
            painter.rotate(self.roll_animation)
            painter.translate(-(x + self.width() // 12), -(y + 22))
            painter.fillRect(x, y + 15, self.width() // 6, 15, self.player_color)
            painter.restore()
        else:
            # Draw normal player
            painter.fillRect(x, y, self.width() // 6, 30, self.player_color)
        
        # Draw boost effect
        if self.boost_mode:
            self.draw_boost_effect(painter, x, y)
    
    def draw_coin(self, painter, x, y):
        size = self.width() // 12
        painter.setBrush(self.coin_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(x, y, size, size)
    
    def draw_powerup(self, painter, x, y, p_type):
        size = self.width() // 9
        painter.setBrush(self.powerup_colors[p_type])
        painter.setPen(Qt.NoPen)
        painter.drawRect(x, y, size, size)
    
    def draw_obstacle(self, painter, x, y, o_type):
        painter.fillRect(
            x, y,
            self.width() // 6,
            20,
            self.obstacle_colors[o_type]
        )
    
    def draw_particles(self, painter):
        for x, y, _, _, life in self.particles:
            alpha = min(255, life * 5)
            color = QColor(255, 255, 255, alpha)
            painter.fillRect(int(x - 1), int(y - 1), 3, 3, color)
        
        for x, y, _, _, life in self.trail_particles:
            alpha = min(255, life * 8)
            color = QColor(self.player_color.red(),
                         self.player_color.green(),
                         self.player_color.blue(),
                         alpha)
            painter.fillRect(int(x - 1), int(y - 1), 3, 3, color)
    
    def draw_boost_effect(self, painter, x, y):
        painter.save()
        painter.setOpacity(0.5)
        for i in range(3):
            offset = i * 5
            painter.fillRect(x - offset, y, self.width() // 6, 30, self.player_color)
        painter.restore()
    
    def draw_hud(self, painter):
        # Draw score and coins
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 10, QFont.Bold))
        painter.drawText(10, 20, f"Score: {self.score}")
        painter.drawText(10, 40, f"Coins: {self.coins}")
        painter.drawText(10, 60, f"Level: {self.level}")
        
        # Draw boost meter if active
        if self.boost_mode:
            painter.fillRect(10, 70, (self.boost_timer / 100) * 50, 5, QColor("#2196F3"))
    
    def draw_game_over(self, painter):
        painter.fillRect(0, 0, self.width(), self.height(), QColor(0, 0, 0, 150))
        painter.setPen(Qt.white)
        painter.setFont(QFont("Arial", 12, QFont.Bold))
        painter.drawText(
            self.rect(),
            Qt.AlignCenter,
            f"Game Over!\nScore: {self.score}\nCoins: {self.coins}\nLevel: {self.level}\nPress R to restart"
        )
    
    def add_jump_particles(self):
        x = self.get_interpolated_x()
        y = self.player_y
        for _ in range(10):
            angle = random.uniform(0, math.pi)
            speed = random.uniform(2, 4)
            dx = math.cos(angle) * speed
            dy = -math.sin(angle) * speed
            self.particles.append([x, y, dx, dy, 20])
    
    def add_trail_particles(self):
        x = self.get_interpolated_x()
        y = self.player_y
        self.trail_particles.append([x, y, 0, 0, 15])
    
    def add_collect_particles(self, pos):
        for _ in range(8):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 3)
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed
            self.particles.append([pos.x(), pos.y(), dx, dy, 30])
    
    def add_explosion_particles(self, pos):
        for _ in range(20):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(2, 5)
            dx = math.cos(angle) * speed
            dy = math.sin(angle) * speed
            self.particles.append([pos.x(), pos.y(), dx, dy, 40])
    
    def activate_powerup(self, powerup_type):
        if powerup_type == 'boost':
            self.boost_mode = True
            self.boost_timer = 100
            self.obstacle_speed = self.base_obstacle_speed * 1.5
        # Add more powerup effects here
    
    def level_up(self):
        self.level += 1
        self.base_obstacle_speed += 0.5
        if not self.boost_mode:
            self.obstacle_speed = self.base_obstacle_speed
    
    def restart_game(self):
        self.player_lane = 1
        self.current_lane_pos = 1
        self.target_lane = 1
        self.player_y = 150
        self.is_jumping = False
        self.is_rolling = False
        self.jump_height = 0
        self.roll_animation = 0
        self.score = 0
        self.coins = 0
        self.level = 1
        self.distance = 0
        self.boost_mode = False
        self.boost_timer = 0
        self.obstacle_speed = self.base_obstacle_speed
        self.game_over = False
        self.obstacles.clear()
        self.coins_list.clear()
        self.powerups.clear()
        self.particles.clear()
        self.trail_particles.clear()
        self.timer.start()
        self.spawn_timer.start()
        self.update()
