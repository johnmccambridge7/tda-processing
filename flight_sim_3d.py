from PyQt5.QtWidgets import QOpenGLWidget
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QVector3D, QMatrix4x4, QQuaternion, QPainter, QColor, QFont
from OpenGL.GL import *
from OpenGL.GLU import *
import math
import random
import numpy as np

class FlightSim3D(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Aircraft state
        self.position = QVector3D(0, 1000, 0)  # x, y (altitude), z
        self.velocity = QVector3D(0, 0, 0)
        self.orientation = QQuaternion()  # Aircraft orientation
        self.thrust = 0
        self.lift = 0
        self.drag = 0
        self.roll_rate = 0
        self.pitch_rate = 0
        self.yaw_rate = 0
        
        # Flight model parameters
        self.mass = 1000  # kg
        self.wing_area = 15  # m²
        self.lift_coefficient = 0.3
        self.drag_coefficient = 0.025
        self.engine_power = 20000  # N
        self.gravity = 9.81  # m/s²
        
        # Camera
        self.camera_mode = 'cockpit'  # or 'chase' or 'orbit'
        self.camera_distance = 10
        self.camera_angle = 0
        
        # Environment
        self.wind = QVector3D(0, 0, 0)
        self.terrain = self.generate_terrain()
        self.clouds = self.generate_clouds()
        
        # Game state
        self.score = 0
        self.game_over = False
        self.waypoints = self.generate_waypoints()
        self.current_waypoint = 0
        
        # Controls state
        self.keys_pressed = set()
        
        # Setup update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_physics)
        self.timer.start(16)  # 60 FPS
        
    def generate_terrain(self):
        """Generate heightmap terrain"""
        size = 100
        terrain = np.zeros((size, size))
        # Simple perlin noise-like terrain
        for x in range(size):
            for z in range(size):
                terrain[x,z] = math.sin(x/10) * math.cos(z/10) * 100
        return terrain
        
    def generate_clouds(self):
        """Generate cloud positions and sizes"""
        clouds = []
        for _ in range(50):
            x = random.uniform(-500, 500)
            y = random.uniform(1000, 2000)
            z = random.uniform(-500, 500)
            size = random.uniform(50, 200)
            clouds.append((QVector3D(x, y, z), size))
        return clouds
        
    def generate_waypoints(self):
        """Generate 3D waypoints for the course"""
        waypoints = []
        radius = 500
        for i in range(10):
            angle = (i / 10) * 2 * math.pi
            x = math.cos(angle) * radius
            z = math.sin(angle) * radius
            y = 1000 + math.sin(angle * 2) * 200
            waypoints.append(QVector3D(x, y, z))
        return waypoints
        
    def initializeGL(self):
        """Initialize OpenGL settings"""
        glClearColor(0.5, 0.7, 1.0, 1.0)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glEnable(GL_COLOR_MATERIAL)
        
    def resizeGL(self, w, h):
        """Handle window resize"""
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w/h, 0.1, 10000.0)
        
    def paintGL(self):
        """Render the scene"""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()
        
        # Set camera position based on mode
        self.setup_camera()
        
        # Draw environment
        self.draw_terrain()
        self.draw_clouds()
        self.draw_waypoints()
        
        # Draw aircraft
        self.draw_aircraft()
        
        # Draw HUD
        self.draw_hud()
        
    def setup_camera(self):
        """Position and orient the camera based on current mode"""
        if self.camera_mode == 'cockpit':
            # Position slightly above and behind aircraft reference point
            eye_pos = self.position + self.orientation.rotatedVector(QVector3D(0, 0.5, -0.5))
            look_pos = self.position + self.orientation.rotatedVector(QVector3D(0, 0, 2))
            up = self.orientation.rotatedVector(QVector3D(0, 1, 0))
        elif self.camera_mode == 'chase':
            # Chase camera
            eye_pos = self.position - self.orientation.rotatedVector(QVector3D(0, -2, -10))
            look_pos = self.position
            up = QVector3D(0, 1, 0)
        else:  # orbit
            # Orbit camera
            eye_pos = QVector3D(
                math.sin(self.camera_angle) * self.camera_distance,
                self.camera_distance * 0.5,
                math.cos(self.camera_angle) * self.camera_distance
            ) + self.position
            look_pos = self.position
            up = QVector3D(0, 1, 0)
            
        gluLookAt(
            eye_pos.x(), eye_pos.y(), eye_pos.z(),
            look_pos.x(), look_pos.y(), look_pos.z(),
            up.x(), up.y(), up.z()
        )
        
    def draw_terrain(self):
        """Draw the terrain mesh"""
        glPushMatrix()
        glColor3f(0.3, 0.5, 0.2)  # Terrain color
        
        size = len(self.terrain)
        scale = 50  # Scale factor for terrain
        
        for x in range(size-1):
            glBegin(GL_TRIANGLE_STRIP)
            for z in range(size):
                # Vertex 1
                glVertex3f(
                    (x - size/2) * scale,
                    self.terrain[x,z],
                    (z - size/2) * scale
                )
                # Vertex 2
                glVertex3f(
                    ((x+1) - size/2) * scale,
                    self.terrain[x+1,z],
                    (z - size/2) * scale
                )
            glEnd()
        glPopMatrix()
        
    def draw_clouds(self):
        """Draw billboard clouds"""
        glPushMatrix()
        glColor4f(1, 1, 1, 0.5)  # White, semi-transparent
        
        for pos, size in self.clouds:
            glPushMatrix()
            glTranslatef(pos.x(), pos.y(), pos.z())
            # Make cloud face camera (billboard technique)
            glRotatef(-self.camera_angle * 180/math.pi, 0, 1, 0)
            
            glBegin(GL_QUADS)
            glVertex3f(-size/2, -size/2, 0)
            glVertex3f(size/2, -size/2, 0)
            glVertex3f(size/2, size/2, 0)
            glVertex3f(-size/2, size/2, 0)
            glEnd()
            
            glPopMatrix()
            
        glPopMatrix()
        
    def draw_waypoints(self):
        """Draw waypoint markers"""
        glPushMatrix()
        
        for i, waypoint in enumerate(self.waypoints):
            if i == self.current_waypoint:
                glColor3f(1, 1, 0)  # Current waypoint in yellow
            else:
                glColor3f(0.5, 0.5, 0.5)  # Other waypoints in gray
                
            glPushMatrix()
            glTranslatef(waypoint.x(), waypoint.y(), waypoint.z())
            
            # Draw ring
            glBegin(GL_LINE_LOOP)
            for angle in range(0, 360, 10):
                rad = math.radians(angle)
                glVertex3f(
                    math.cos(rad) * 50,
                    math.sin(rad) * 50,
                    0
                )
            glEnd()
            
            glPopMatrix()
            
        glPopMatrix()
        
    def draw_aircraft(self):
        """Draw the aircraft model"""
        glPushMatrix()
        
        # Transform to aircraft position and orientation
        glTranslatef(self.position.x(), self.position.y(), self.position.z())
        rot_matrix = QMatrix4x4()
        rot_matrix.rotate(self.orientation)
        glMultMatrixf(rot_matrix.data())
        
        glColor3f(0.7, 0.7, 0.7)  # Aircraft color
        
        # Draw fuselage
        glPushMatrix()
        glScalef(0.5, 0.5, 2.0)
        self.draw_box()
        glPopMatrix()
        
        # Draw wings
        glPushMatrix()
        glTranslatef(0, 0, 0)
        glScalef(3.0, 0.1, 0.5)
        self.draw_box()
        glPopMatrix()
        
        # Draw tail
        glPushMatrix()
        glTranslatef(0, 0.5, -1.5)
        glScalef(0.5, 1.0, 0.1)
        self.draw_box()
        glPopMatrix()
        
        glPopMatrix()
        
    def draw_box(self):
        """Draw a unit cube"""
        glBegin(GL_QUADS)
        # Front
        glVertex3f(-0.5, -0.5, 0.5)
        glVertex3f(0.5, -0.5, 0.5)
        glVertex3f(0.5, 0.5, 0.5)
        glVertex3f(-0.5, 0.5, 0.5)
        # Back
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, 0.5, -0.5)
        glVertex3f(0.5, 0.5, -0.5)
        glVertex3f(0.5, -0.5, -0.5)
        # Top
        glVertex3f(-0.5, 0.5, -0.5)
        glVertex3f(-0.5, 0.5, 0.5)
        glVertex3f(0.5, 0.5, 0.5)
        glVertex3f(0.5, 0.5, -0.5)
        # Bottom
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(0.5, -0.5, -0.5)
        glVertex3f(0.5, -0.5, 0.5)
        glVertex3f(-0.5, -0.5, 0.5)
        # Right
        glVertex3f(0.5, -0.5, -0.5)
        glVertex3f(0.5, 0.5, -0.5)
        glVertex3f(0.5, 0.5, 0.5)
        glVertex3f(0.5, -0.5, 0.5)
        # Left
        glVertex3f(-0.5, -0.5, -0.5)
        glVertex3f(-0.5, -0.5, 0.5)
        glVertex3f(-0.5, 0.5, 0.5)
        glVertex3f(-0.5, 0.5, -0.5)
        glEnd()
        
    def draw_hud(self):
        """Draw heads-up display"""
        glMatrixMode(GL_PROJECTION)
        glPushMatrix()
        glLoadIdentity()
        glOrtho(0, self.width(), self.height(), 0, -1, 1)
        
        glMatrixMode(GL_MODELVIEW)
        glPushMatrix()
        glLoadIdentity()
        
        glDisable(GL_DEPTH_TEST)
        glColor3f(0, 1, 0)  # Green HUD
        
        # Draw text using OpenGL
        painter = QPainter(self)
        painter.setFont(QFont("Arial", 10))
        painter.setPen(QColor(0, 255, 0))  # Green color for HUD
        painter.drawText(10, 20, f"Altitude: {int(self.position.y())}m")
        painter.drawText(10, 40, f"Speed: {int(self.velocity.length())}m/s")
        painter.drawText(10, 60, f"Score: {self.score}")
        
        if self.game_over:
            painter.drawText(
                self.rect(),
                Qt.AlignCenter,
                "Game Over! Press R to restart"
            )
            
        glEnable(GL_DEPTH_TEST)
        
        glPopMatrix()
        glMatrixMode(GL_PROJECTION)
        glPopMatrix()
        glMatrixMode(GL_MODELVIEW)
        
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_R and self.game_over:
            self.restart_game()
            return
            
        self.keys_pressed.add(event.key())
        
        # Camera controls
        if event.key() == Qt.Key_V:
            modes = ['cockpit', 'chase', 'orbit']
            current_idx = modes.index(self.camera_mode)
            self.camera_mode = modes[(current_idx + 1) % len(modes)]
            
    def keyReleaseEvent(self, event):
        """Handle key release events"""
        self.keys_pressed.discard(event.key())
        
    def update_physics(self):
        """Update flight physics"""
        if self.game_over:
            return
            
        dt = 0.016  # 60 FPS
        
        # Handle input
        self.handle_flight_controls(dt)
        
        # Calculate forces
        forces = self.calculate_forces()
        
        # Update velocity
        acceleration = forces / self.mass
        self.velocity += acceleration * dt
        
        # Update position
        self.position += self.velocity * dt
        
        # Check collisions
        if self.position.y() <= self.get_terrain_height(self.position.x(), self.position.z()):
            self.game_over = True
            
        # Check waypoints
        self.check_waypoints()
        
        self.update()
        
    def handle_flight_controls(self, dt):
        """Process control inputs"""
        # Pitch (W/S)
        if Qt.Key_W in self.keys_pressed:
            self.pitch_rate = -1
        elif Qt.Key_S in self.keys_pressed:
            self.pitch_rate = 1
        else:
            self.pitch_rate = 0
            
        # Roll (A/D)
        if Qt.Key_A in self.keys_pressed:
            self.roll_rate = -1
        elif Qt.Key_D in self.keys_pressed:
            self.roll_rate = 1
        else:
            self.roll_rate = 0
            
        # Yaw (Q/E)
        if Qt.Key_Q in self.keys_pressed:
            self.yaw_rate = -1
        elif Qt.Key_E in self.keys_pressed:
            self.yaw_rate = 1
        else:
            self.yaw_rate = 0
            
        # Thrust (Space/Ctrl)
        if Qt.Key_Space in self.keys_pressed:
            self.thrust = min(self.thrust + dt, 1.0)
        elif Qt.Key_Control in self.keys_pressed:
            self.thrust = max(self.thrust - dt, 0.0)
            
        # Update orientation
        pitch_rotation = QQuaternion.fromAxisAndAngle(QVector3D(1, 0, 0), self.pitch_rate * 50 * dt)
        roll_rotation = QQuaternion.fromAxisAndAngle(QVector3D(0, 0, 1), self.roll_rate * 50 * dt)
        yaw_rotation = QQuaternion.fromAxisAndAngle(QVector3D(0, 1, 0), self.yaw_rate * 50 * dt)
        
        self.orientation = pitch_rotation * roll_rotation * yaw_rotation * self.orientation
        self.orientation.normalize()
        
    def calculate_forces(self):
        """Calculate all forces acting on the aircraft"""
        # Thrust
        thrust_force = self.orientation.rotatedVector(
            QVector3D(0, 0, self.thrust * self.engine_power)
        )
        
        # Lift
        airspeed = self.velocity.length()
        if airspeed > 0:
            lift_direction = QVector3D.crossProduct(
                self.orientation.rotatedVector(QVector3D(1, 0, 0)),
                self.velocity.normalized()
            )
            lift = 0.5 * 1.225 * airspeed * airspeed * self.wing_area * self.lift_coefficient
            lift_force = lift_direction.normalized() * lift
        else:
            lift_force = QVector3D(0, 0, 0)
            
        # Drag
        if airspeed > 0:
            drag = 0.5 * 1.225 * airspeed * airspeed * self.wing_area * self.drag_coefficient
            drag_force = -self.velocity.normalized() * drag
        else:
            drag_force = QVector3D(0, 0, 0)
            
        # Gravity
        gravity_force = QVector3D(0, -self.mass * self.gravity, 0)
        
        # Total force
        return thrust_force + lift_force + drag_force + gravity_force
        
    def get_terrain_height(self, x, z):
        """Get terrain height at given coordinates"""
        size = len(self.terrain)
        scale = 50
        
        # Convert world coordinates to terrain array indices
        terrain_x = int((x / scale + size/2) % size)
        terrain_z = int((z / scale + size/2) % size)
        
        return self.terrain[terrain_x, terrain_z]
        
    def check_waypoints(self):
        """Check if aircraft has reached current waypoint"""
        if self.current_waypoint < len(self.waypoints):
            waypoint = self.waypoints[self.current_waypoint]
            dist = (self.position - waypoint).length()
            
            if dist < 50:  # Waypoint radius
                self.score += 100
                self.current_waypoint += 1
                
    def restart_game(self):
        """Reset the game state"""
        self.position = QVector3D(0, 1000, 0)
        self.velocity = QVector3D(0, 0, 0)
        self.orientation = QQuaternion()
        self.thrust = 0
        self.roll_rate = 0
        self.pitch_rate = 0
        self.yaw_rate = 0
        self.score = 0
        self.game_over = False
        self.current_waypoint = 0
        self.camera_mode = 'cockpit'
