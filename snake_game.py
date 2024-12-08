from PyQt5.QtWidgets import QWidget, QGridLayout, QSizePolicy
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QPainter, QColor, QKeyEvent
import random

class SnakeGame(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(200, 200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Game state
        self.snake = [QPoint(5, 5)]
        self.food = QPoint(15, 15)
        self.direction = QPoint(1, 0)  # Moving right initially
        self.score = 0
        self.game_over = False
        
        # Game settings
        self.cell_size = 10  # Smaller cells to fit 50x50 grid
        self.grid_size = 50
        self.game_speed = 100  # milliseconds
        
        # Setup game timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.move_snake)
        self.timer.start(self.game_speed)
        
        # Colors
        self.snake_color = QColor("#4CAF50")
        self.food_color = QColor("#F44336")
        self.background_color = QColor("#2E2E2E")
        self.grid_color = QColor("#3E3E3E")
        
    def paintEvent(self, event):
        painter = QPainter(self)
        
        # Draw background
        painter.fillRect(0, 0, self.width(), self.height(), self.background_color)
        
        # Draw grid
        for x in range(0, self.width(), self.cell_size):
            for y in range(0, self.height(), self.cell_size):
                painter.setPen(self.grid_color)
                painter.drawRect(x, y, self.cell_size, self.cell_size)
        
        # Draw snake
        painter.setBrush(self.snake_color)
        for segment in self.snake:
            painter.fillRect(
                segment.x() * self.cell_size,
                segment.y() * self.cell_size,
                self.cell_size - 1,
                self.cell_size - 1,
                self.snake_color
            )
        
        # Draw food
        painter.setBrush(self.food_color)
        painter.fillRect(
            self.food.x() * self.cell_size,
            self.food.y() * self.cell_size,
            self.cell_size - 1,
            self.cell_size - 1,
            self.food_color
        )
        
        # Draw game over text
        if self.game_over:
            painter.setPen(Qt.white)
            painter.drawText(self.rect(), Qt.AlignCenter, f"Game Over!\nScore: {self.score}\nPress R to restart")
            
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        
        if key == Qt.Key_R and self.game_over:
            self.restart_game()
            return
            
        if self.game_over:
            return
            
        if key == Qt.Key_Left and self.direction.x() != 1:
            self.direction = QPoint(-1, 0)
        elif key == Qt.Key_Right and self.direction.x() != -1:
            self.direction = QPoint(1, 0)
        elif key == Qt.Key_Up and self.direction.y() != 1:
            self.direction = QPoint(0, -1)
        elif key == Qt.Key_Down and self.direction.y() != -1:
            self.direction = QPoint(0, 1)
            
    def move_snake(self):
        if self.game_over:
            return
            
        # Calculate new head position
        new_head = QPoint(
            (self.snake[0].x() + self.direction.x()) % self.grid_size,
            (self.snake[0].y() + self.direction.y()) % self.grid_size
        )
        
        # Check for collision with self
        if new_head in self.snake:
            self.game_over = True
            self.timer.stop()
            self.update()
            return
            
        # Move snake
        self.snake.insert(0, new_head)
        
        # Check for food
        if new_head == self.food:
            self.score += 1
            self.spawn_food()
        else:
            self.snake.pop()
            
        self.update()
        
    def spawn_food(self):
        while True:
            x = random.randint(0, self.grid_size - 1)
            y = random.randint(0, self.grid_size - 1)
            new_food = QPoint(x, y)
            if new_food not in self.snake:
                self.food = new_food
                break
                
    def restart_game(self):
        self.snake = [QPoint(5, 5)]
        self.direction = QPoint(1, 0)
        self.score = 0
        self.game_over = False
        self.spawn_food()
        self.timer.start()
        self.update()
        
    def resizeEvent(self, event):
        # Make height match width to maintain square aspect ratio
        self.setFixedHeight(self.width())
        super().resizeEvent(event)
