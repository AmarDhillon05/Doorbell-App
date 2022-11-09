#All the imports
import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
import mysql.connector
import socket
from kivy.clock import Clock
import numpy as np
import cv2
import pickle

kivy.require('2.0.0')


class CameraViewPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cols = 3
        self.size = 50, 40
        self.row_default_width = 40
        self.row_default_height = 25

        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect(('127.0.0.1', 5000)) #Local for now bc problems
        
        #The actual layout
        self.add_empty_space(1)
        self.add_widget(Label(text = f"({app.current_name})"))
        self.detect_people_button = Button(text = "Detect people")
        self.detect_people_button.bind(on_press = self.detect_faces)
        self.add_widget(self.detect_people_button)
        self.add_empty_space(1)

        self.cam_img = Image(source = 'cam_input.png') #Placeholder incase nothing is detected
        self.add_widget(self.cam_img)

        self.status_text = Label(text = "Nobody Found")
        self.add_widget(self.status_text)
        self.add_empty_space(3)
        #End of layout

        def update_info(inst): #This while loop works
            recv = self.conn.recv(1843200)
            try: #If Text Data 
                text = recv.decode('utf-8')
                self.status_text.text = text
            except Exception as e: #Elif Image data

                #JUST HAVE TO GET THISS WORKING
                #WIll FIX THIS LATER
                img = np.frombuffer(recv, dtype = np.int64)
                if img.shape[0] == 28800: #Most common shape
                    img = img.reshape(100, 96, 3)
                    texture = Texture.create(size = (96, 100))
                    texture.blit_buffer(img.tobytes(), bufferfmt = 'ubyte')
                    self.cam_img.texture = texture
                    cv2.imwrite('Cap.png', img)
                else:
                    print(img.shape[0])
        

        Clock.schedule_interval(update_info, 1/60)
        
    def detect_faces(self, inst):
        self.conn.send('Show faces'.encode('utf-8'))

    def add_empty_space(self, c):
        for _ in range(c):
            self.add_widget(Label(text = ''))

#Camera select and join page
class CameraBoardPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cols = 3
        self.size = 50, 40
        self.row_default_height = 40
        self.row_force_default = True

        self.widgets = []

        #Button to load layout since the cams don't load for some reason
        self.load_layout_button = Button(text = 'Refresh')
        self.load_layout_button.bind(on_press = self.load_layout)
        self.add_widget(self.load_layout_button)
        self.add_empty_space(2, widg = False)


    def load_layout(self, inst):
        for widg in self.widgets:
            self.remove_widget(widg)
        self.widgets = []

        self.add_empty_space(3)
        self.reload_cams()
        self.add_empty_space(3)
        cam_label = Label(text = 'Add Camera')
        self.widgets.append(cam_label)
        self.add_widget(cam_label)
        self.add_cam_box = TextInput(multiline = False)
        self.widgets.append(self.add_cam_box)
        self.add_widget(self.add_cam_box)
        self.add_cam_button = Button(text = 'Add Camera')
        self.add_cam_button.bind(on_press = self.add_camera)
        self.widgets.append(self.add_cam_button)
        self.add_widget(self.add_cam_button)

    def add_empty_space(self, count, widg = True):
        for _ in range(count):
            empt = Label(text = '')
            self.add_widget(empt)
            if widg:
                self.widgets.append(empt)

    #My local: 192.168.1.35
    def add_camera(self, inst):
        ip = self.add_cam_box.text
        name = ''
        app.cursor.execute(
            f"SELECT name FROM cams WHERE ip = '{ip}'"
        )
        for n in app.cursor:
            name = n
        if name == '':
            self.add_cam_box.text = 'Invalid Name'
        else:
            app.cursor.execute(f"SELECT cams FROM users WHERE pwd = '{app.pwd}'")
            for x in app.cursor:
                if name[0] in x[0]:
                    self.add_cam_box.text = f'Already have {name[0]}'
                else:
                    # (ip, name)|(ip, name)|(ip, name)
                    cams = x[0]
                    new_text = cams + f"({ip},{name[0]})|"
                    print(new_text)
                    app.cursor.execute(f"UPDATE users SET cams = '{new_text}' WHERE pwd = '{app.pwd}'")
                    app.camdb.commit()
                    self.add_cam_box.text = f"Successfully Added {name[0]}"


    def reload_cams(self):
        self.buttons, self.funcs = [], []
        app.cursor.execute(f"SELECT cams FROM users WHERE pwd = '{app.pwd}'")
        for x, in app.cursor:
            for entry in x.split('|')[:-1]:  #Since the split will have one at the end
                entry = entry.replace('(', '').replace(')', '').split(',')
                ip = entry[0]; name = entry[-1]
                cam_button = Button(text = f"Go to {name}")
                def cam_func(self):
                    app.current_ip = ip
                    app.current_name = name
                    app.screen_manager.current = 'Camview'
                cam_button.bind(on_press = cam_func)
                self.add_empty_space(1)
                self.add_widget(cam_button)
                self.add_empty_space(1)
                self.widgets.append(cam_button)
        

#Logging in to an Account
class LoginPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cols = 4
        self.size = 50, 40
        self.row_default_height = 25
        self.row_default_width = 40
        self.row_force_default = True
        self.add_empty_space(5)
        self.add_widget(Label(text = 'Login with Pwd'))
        self.add_empty_space(3)
        self.login_box = TextInput(multiline = False)
        self.add_widget(self.login_box)
        self.submit_button = Button(text = 'Submit')
        self.submit_button.bind(on_press = self.login_buttonfunc)
        self.add_widget(self.submit_button)
        self.add_empty_space(2)
        self.success_text = Label(text = '')
        self.add_widget(self.success_text)
        self.goto_create_page = Button(text = 'Create Instead')
        self.goto_create_page.bind(on_press = self.goto_create)
        self.add_widget(self.goto_create_page)

    def login(self, pwd):
        success = False
        app.cursor.execute('SELECT pwd FROM users')
        for x in app.cursor:
            if pwd in x:
                success = True
        if success:
            self.success_text.text = f'Welcome, {pwd}'
            app.pwd = pwd
            app.screen_manager.current = 'Camboard'
        else:
            self.success_text.text = 'Pwd Invalid!'

    def login_buttonfunc(self, instance):
        self.login(self.login_box.text)

    def add_empty_space(self, cells):
        for _ in range(cells):
            self.add_widget(Label(text = ' '))

    def goto_create(self, instance):
        app.screen_manager.current = 'Create'

#Creating an Account
class CreatePage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cols = 4 #For empty space
        self.size = 50, 40
        self.row_default_width = 40
        self.row_default_height = 25
        self.row_force_default = True
        self.add_empty_space(5)
        self.add_widget(Label(text = 'Create with Pwd'))
        self.add_empty_space(3)
        self.login_box = TextInput(multiline = False)
        self.add_widget(self.login_box)
        self.submit_button = Button(text = 'Create and Login')
        self.submit_button.bind(on_press = self.create)
        self.add_widget(self.submit_button)
        self.add_empty_space(2)
        self.success_text = Label(text = '')
        self.add_widget(self.success_text)
        self.goto_login_page = Button(text = 'Login Instead')
        self.goto_login_page.bind(on_press = self.goto_login)
        self.add_widget(self.goto_login_page)

    def create(self, instance):
        pwd = self.login_box.text
        if len(pwd) > 5:
            success = True
            app.cursor.execute('SELECT pwd FROM users')
            for x in app.cursor:
                if pwd in x:
                    success = False
                    self.success_text.text = 'Pwd in use!'
            if success:
                app.cursor.execute(f"INSERT INTO users (pwd, cams) VALUES ('{pwd}', '')")
                app.camdb.commit()
                app.login_page.login(pwd)
        else:
            self.success_text.text = 'Pwd too short!'

    def add_empty_space(self, cells):
        for _ in range(cells):
            self.add_widget(Label(text = ' '))

    def goto_login(self, instance):
        app.screen_manager.current = 'Login'

#App Class
class TheApp(App):
    def build(self):
        self.pwd = ''
        self.current_ip = ''
        self.current_name = ''

        self.camdb = mysql.connector.connect(
            host = 'localhost',
            user = 'root',
            passwd = 'Rb878425!',
            database = 'camdb'
        )
        self.cursor = self.camdb.cursor()

        self.screen_manager = ScreenManager()

        #Page Classes and data stored here
        self.login_page = LoginPage()
        login = Screen(name = 'Login')
        login.add_widget(self.login_page)
        self.screen_manager.add_widget(login)

        self.create_page = CreatePage()
        create = Screen(name = 'Create')
        create.add_widget(self.create_page)
        self.screen_manager.add_widget(create)

        self.cam_board_page = CameraBoardPage()
        camboard = Screen(name = 'Camboard')
        camboard.add_widget(self.cam_board_page)
        self.screen_manager.add_widget(camboard)

        self.cam_view_page = CameraViewPage()
        camview = Screen(name = 'Camview')
        camview.add_widget(self.cam_view_page)
        self.screen_manager.add_widget(camview)

        return self.screen_manager

app = TheApp()
app.run()


#Because I can't run a deep learning model all the time,
#I will just add a button to detect the faces