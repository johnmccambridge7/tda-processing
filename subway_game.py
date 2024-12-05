from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QPainter, QColor, QKeyEvent
import random

class SubwayGame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)  # Compact size
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Game state
        self.player_lane = 1  # 0=left, 1=center, 2=right
        self.player_y = 150
        self.is_jumping = False
        self.jump_height = 0
        self.score = 0
        self.game_over = False
        
        # Obstacles
        self.obstacles = []  # [lane, y_pos]
        self.obstacle_speed = 3
        
        # Colors
        self.player_color = QColor("#4CAF50")
        self.obstacle_color = QColor("#F44336")
        self.background_color = QColor("#2E2E2E")
        
        # Setup game timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_game)
        self.timer.start(16)  # ~60 FPS
        
        # Spawn obstacles periodically
        self.spawn_timer = QTimer(self)
        self.spawn_timer.timeout.connect(self.spawn_obstacle)
        self.spawn_timer.start(2000)  # Spawn every 2 seconds
        
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw background
        painter.fillRect(0, 0, self.width(), self.height(), self.background_color)
        
        # Draw lanes
        lane_width = self.width() // 3
        for i in range(3):
            painter.setPen(QColor("#3E3E3E"))
            x = i * lane_width
            painter.drawLine(x, 0, x, self.height())
        
        # Draw player
        player_x = (self.player_lane * lane_width) + (lane_width // 4)
        player_y = self.player_y - self.jump_height
        painter.fillRect(
            player_x, player_y,
            lane_width // 2, 30,
            self.player_color
        )
        
        # Draw obstacles
        for obstacle in self.obstacles:
            lane, y_pos = obstacle
            x = (lane * lane_width) + (lane_width // 4)
            painter.fillRect(
                x, y_pos,
                lane_width // 2, 20,
                self.obstacle_color
            )
        
        # Draw score
        painter.setPen(Qt.white)
        painter.drawText(10, 20, f"Score: {self.score}")
        
        if self.game_over:
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                f"Game Over!\nScore: {self.score}\nPress R to restart"
            )
    
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_R and self.game_over:
            self.restart_game()
            return
            
        if self.game_over:
            return
            
        if event.key() == Qt.Key_Left and self.player_lane > 0:
            self.player_lane -= 1
        elif event.key() == Qt.Key_Right and self.player_lane < 2:
            self.player_lane += 1
        elif event.key() == Qt.Key_Space and not self.is_jumping:
            self.is_jumping = True
            self.jump_height = 0
    
    def update_game(self):
        if self.game_over:
            return
            
        # Update jump
        if self.is_jumping:
            self.jump_height += 5
            if self.jump_height >= 50:  # Max jump height
                self.is_jumping = False
        elif self.jump_height > 0:
            self.jump_height -= 5
        
        # Update obstacles
        for obstacle in self.obstacles[:]:
            obstacle[1] += self.obstacle_speed
            if obstacle[1] > self.height():
                self.obstacles.remove(obstacle)
                self.score += 1
                
            # Collision detection
            lane_width = self.width() // 3
            player_rect = QRect(
                (self.player_lane * lane_width) + (lane_width // 4),
                self.player_y - self.jump_height,
                lane_width // 2,
                30
            )
            obstacle_rect = QRect(
                (obstacle[0] * lane_width) + (lane_width // 4),
                obstacle[1],
                lane_width // 2,
                20
            )
            
            if player_rect.intersects(obstacle_rect):
                self.game_over = True
                self.timer.stop()
                self.spawn_timer.stop()
        
        self.update()
    
    def spawn_obstacle(self):
        if not self.game_over:
            lane = random.randint(0, 2)
            self.obstacles.append([lane, -20])
    
    def restart_game(self):
        self.player_lane = 1
        self.player_y = 150
        self.is_jumping = False
        self.jump_height = 0
        self.score = 0
        self.game_over = False
        self.obstacles.clear()
        self.timer.start()
        self.spawn_timer.start()
        self.update()
