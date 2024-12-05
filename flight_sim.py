from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import Qt, QTimer, QPointF
from PyQt5.QtGui import QPainter, QColor, QKeyEvent, QLinearGradient, QPen, QFont, QTransform
import math
import random

class FlightSim(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Aircraft state
        self.position = QPointF(100, 100)  # x, y in screen coordinates
        self.altitude = 1000  # feet
        self.heading = 0  # degrees
        self.pitch = 0  # degrees
        self.roll = 0  # degrees
        self.airspeed = 120  # knots
        self.vertical_speed = 0  # feet per minute
        
        # Flight dynamics
        self.thrust = 0
        self.elevator = 0
        self.ailerons = 0
        self.flaps = 0
        self.gear_down = True
        self.stall_speed = 60  # knots
        
        # Environment
        self.wind_speed = random.uniform(0, 15)
        self.wind_direction = random.uniform(0, 360)
        self.turbulence = 0
        self.clouds = self.generate_clouds()
        
        # Game state
        self.score = 0
        self.game_over = False
        self.landing_successful = False
        self.mission_waypoints = self.generate_waypoints()
        self.current_waypoint = 0
        
        # Controls
        self.keys_pressed = set()
        
        # Visual effects
        self.contrails = []  # [(x, y, alpha), ...]
        self.particles = []  # [(x, y, dx, dy, life), ...]
        
        # Timer setup
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(16)  # ~60 FPS
        
    def generate_clouds(self):
        """Generate random cloud formations"""
        clouds = []
        for _ in range(10):
            x = random.uniform(0, self.width())
            y = random.uniform(0, self.height())
            size = random.uniform(20, 50)
            clouds.append((x, y, size))
        return clouds
        
    def generate_waypoints(self):
        """Generate mission waypoints"""
        waypoints = []
        for _ in range(5):
            x = random.uniform(50, self.width() - 50)
            y = random.uniform(50, self.height() - 50)
            alt = random.uniform(500, 5000)
            waypoints.append((x, y, alt))
        return waypoints
        
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_R and self.game_over:
            self.restart_simulation()
            return
            
        self.keys_pressed.add(event.key())
        
    def keyReleaseEvent(self, event: QKeyEvent):
        self.keys_pressed.discard(event.key())
        
    def update_simulation(self):
        if self.game_over:
            return
            
        # Handle flight controls
        if Qt.Key_W in self.keys_pressed:  # Pitch down
            self.pitch = max(self.pitch - 2, -30)
        if Qt.Key_S in self.keys_pressed:  # Pitch up
            self.pitch = min(self.pitch + 2, 30)
        if Qt.Key_A in self.keys_pressed:  # Roll left
            self.roll = max(self.roll - 3, -60)
        if Qt.Key_D in self.keys_pressed:  # Roll right
            self.roll = min(self.roll + 3, 60)
        if Qt.Key_Q in self.keys_pressed:  # Yaw left
            self.heading = (self.heading - 1) % 360
        if Qt.Key_E in self.keys_pressed:  # Yaw right
            self.heading = (self.heading + 1) % 360
        if Qt.Key_Space in self.keys_pressed:  # Increase thrust
            self.thrust = min(self.thrust + 0.1, 1.0)
        if Qt.Key_Control in self.keys_pressed:  # Decrease thrust
            self.thrust = max(self.thrust - 0.1, 0.0)
        if Qt.Key_G in self.keys_pressed:  # Toggle gear
            self.gear_down = not self.gear_down
        if Qt.Key_F in self.keys_pressed:  # Toggle flaps
            self.flaps = min(self.flaps + 0.1, 1.0)
            
        # Natural stability
        self.pitch *= 0.95  # Return to level
        self.roll *= 0.9   # Self-correcting roll
        
        # Update physics
        self.update_flight_physics()
        
        # Check for stall
        if self.airspeed < self.stall_speed:
            self.pitch -= 5  # Nose drops in stall
            self.add_stall_buffet()
            
        # Update effects
        self.update_effects()
        
        # Check waypoints
        self.check_waypoints()
        
        # Check for crash
        if self.altitude <= 0:
            if self.airspeed < 100 and abs(self.pitch) < 10 and self.gear_down:
                self.landing_successful = True
                self.score += 1000
            else:
                self.game_over = True
            
        self.update()
        
    def update_flight_physics(self):
        # Basic flight model
        gravity = 32.2  # ft/s²
        lift_coefficient = math.cos(math.radians(self.roll)) * (1 + self.flaps * 0.5)
        drag_coefficient = 0.03 + self.flaps * 0.1 + (self.gear_down * 0.05)
        
        # Airspeed changes
        thrust_force = self.thrust * 500  # Max thrust
        drag_force = (self.airspeed ** 2) * drag_coefficient
        self.airspeed += (thrust_force - drag_force) * 0.01
        self.airspeed = max(0, self.airspeed)
        
        # Altitude changes
        lift = (self.airspeed ** 2) * lift_coefficient * math.sin(math.radians(self.pitch))
        self.vertical_speed = (lift - gravity) * 60  # Convert to feet per minute
        self.altitude += self.vertical_speed * 0.016  # 16ms frame time
        
        # Position updates
        heading_rad = math.radians(self.heading)
        ground_speed = self.airspeed + (self.wind_speed * math.cos(math.radians(self.wind_direction - self.heading)))
        
        self.position += QPointF(
            math.sin(heading_rad) * ground_speed * 0.05,
            -math.cos(heading_rad) * ground_speed * 0.05
        )
        
        # Wrap around screen
        self.position.setX(self.position.x() % self.width())
        self.position.setY(self.position.y() % self.height())
        
    def update_effects(self):
        # Update contrails
        if self.altitude > 3000 and self.airspeed > 150:
            self.contrails.append((self.position.x(), self.position.y(), 255))
        
        # Fade and remove old contrails
        self.contrails = [(x, y, a - 2) for x, y, a in self.contrails if a > 0]
        
        # Update particles
        for particle in self.particles[:]:
            particle[0] += particle[2]
            particle[1] += particle[3]
            particle[4] -= 1
            if particle[4] <= 0:
                self.particles.remove(particle)
                
    def add_stall_buffet(self):
        """Add turbulence particles during stall"""
        for _ in range(2):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(1, 3)
            self.particles.append([
                self.position.x(),
                self.position.y(),
                math.cos(angle) * speed,
                math.sin(angle) * speed,
                10
            ])
            
    def check_waypoints(self):
        """Check if aircraft has reached current waypoint"""
        if self.current_waypoint < len(self.mission_waypoints):
            wx, wy, walt = self.mission_waypoints[self.current_waypoint]
            dist = math.sqrt((self.position.x() - wx)**2 + (self.position.y() - wy)**2)
            alt_diff = abs(self.altitude - walt)
            
            if dist < 20 and alt_diff < 500:
                self.score += 100
                self.current_waypoint += 1
                
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw sky gradient
        sky = QLinearGradient(0, 0, 0, self.height())
        sky.setColorAt(0, QColor("#1E88E5"))
        sky.setColorAt(1, QColor("#64B5F6"))
        painter.fillRect(0, 0, self.width(), self.height(), sky)
        
        # Draw clouds
        painter.setPen(Qt.NoPen)
        for x, y, size in self.clouds:
            cloud_gradient = QLinearGradient(x, y, x, y + size)
            cloud_gradient.setColorAt(0, QColor(255, 255, 255, 200))
            cloud_gradient.setColorAt(1, QColor(255, 255, 255, 100))
            painter.setBrush(cloud_gradient)
            painter.drawEllipse(QPointF(x, y), size, size/2)
            
        # Draw contrails
        for x, y, alpha in self.contrails:
            painter.setPen(QPen(QColor(255, 255, 255, alpha), 2))
            painter.drawPoint(int(x), int(y))
            
        # Draw particles
        for x, y, _, _, life in self.particles:
            alpha = min(255, life * 25)
            painter.setPen(QPen(QColor(255, 255, 255, alpha), 2))
            painter.drawPoint(int(x), int(y))
            
        # Draw waypoints
        painter.setPen(QPen(QColor("#FFD700"), 2))
        for i, (wx, wy, _) in enumerate(self.mission_waypoints):
            if i == self.current_waypoint:
                painter.setBrush(QColor("#FFD700"))
            else:
                painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(QPointF(wx, wy), 10, 10)
            
        # Draw aircraft
        painter.save()
        painter.translate(self.position)
        painter.rotate(-self.heading)
        painter.rotate(self.roll)
        
        # Aircraft body
        painter.setBrush(QColor("#FFFFFF"))
        painter.setPen(QPen(QColor("#333333"), 1))
        
        # Draw fuselage
        painter.drawRect(-15, -3, 30, 6)
        
        # Draw wings
        wing_path = QTransform()
        wing_path.translate(-5, 0)
        painter.drawRect(-12, -15, 24, 4)  # Main wing
        painter.drawRect(-8, 8, 16, 3)     # Rear wing
        painter.drawRect(-2, -8, 4, 16)    # Vertical stabilizer
        
        # Draw landing gear if down
        if self.gear_down:
            painter.setBrush(QColor("#666666"))
            painter.drawRect(-10, 3, 2, 5)
            painter.drawRect(8, 3, 2, 5)
            
        painter.restore()
        
        # Draw HUD
        painter.setPen(QColor("#00FF00"))
        painter.setFont(QFont("Arial", 8))
        
        # Altitude tape
        alt_str = f"{int(self.altitude):,}'"
        painter.drawText(10, 20, f"ALT: {alt_str}")
        
        # Airspeed tape
        painter.drawText(10, 35, f"IAS: {int(self.airspeed)}kt")
        
        # Vertical speed
        vs_str = f"{int(self.vertical_speed):+,}"
        painter.drawText(10, 50, f"VS: {vs_str}fpm")
        
        # Heading
        painter.drawText(10, 65, f"HDG: {int(self.heading):03d}°")
        
        # Score
        painter.drawText(10, 80, f"Score: {self.score}")
        
        # Warning indicators
        if self.airspeed < self.stall_speed + 10:
            painter.setPen(QColor("#FF0000"))
            painter.drawText(self.width() - 60, 20, "STALL")
            
        if self.altitude < 1000 and not self.gear_down:
            painter.setPen(QColor("#FF0000"))
            painter.drawText(self.width() - 60, 35, "GEAR")
            
        if self.game_over:
            painter.fillRect(0, 0, self.width(), self.height(), QColor(0, 0, 0, 150))
            painter.setPen(Qt.white)
            painter.setFont(QFont("Arial", 12, QFont.Bold))
            
            if self.landing_successful:
                message = f"Landing Successful!\nScore: {self.score}"
            else:
                message = f"Crash!\nScore: {self.score}"
                
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                f"{message}\nPress R to restart"
            )
            
    def restart_simulation(self):
        """Reset the simulation state"""
        self.position = QPointF(100, 100)
        self.altitude = 1000
        self.heading = 0
        self.pitch = 0
        self.roll = 0
        self.airspeed = 120
        self.vertical_speed = 0
        self.thrust = 0.5
        self.elevator = 0
        self.ailerons = 0
        self.flaps = 0
        self.gear_down = True
        self.score = 0
        self.game_over = False
        self.landing_successful = False
        self.current_waypoint = 0
        self.mission_waypoints = self.generate_waypoints()
        self.contrails.clear()
        self.particles.clear()
        self.timer.start()
