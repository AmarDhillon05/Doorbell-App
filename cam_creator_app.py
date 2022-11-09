import kivy
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.graphics.texture import Texture #Used in images
from kivy.clock import Clock
import socket
import mysql.connector
import os
import cv2
from model_load import return_marked_image_with_status
from mtcnn import MTCNN
import threading
#Takes a while to load, one day I'll find out how to optimize this

kivy.require('2.0.0')

class MakeCamPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.cols = 4
        self.size = 50, 40
        self.row_default_width = 40
        self.row_default_height = 25
        self.row_force_default = True

        self.local_ip = socket.gethostbyname(socket.gethostname())

        self.add_empty_space(5)
        self.add_widget(Label(text = 'Create New Cam'))
        self.add_widget(Label(text = f"Ip: {self.local_ip}"))
        self.add_empty_space(2)
        self.cam_name_box = TextInput(multiline = False)
        self.add_widget(self.cam_name_box)
        self.submit_button = Button(text = 'Submit')
        self.submit_button.bind(on_press = self.Submit)
        self.add_widget(self.submit_button)


    def add_empty_space(self, c):
        for _ in range(c):
            self.add_widget(Label(text = ''))

    def Submit(self, instance):
        name = self.cam_name_box.text
        app.cursor.execute(f"INSERT INTO cams (ip, name) VALUES ('{self.local_ip}', '{name}')")
        app.db.commit()
        app.screen_manager.current = 'Display'


class DisplayPage(GridLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.local_ip = socket.gethostbyname(socket.gethostname())
        self.cam_name = ''
        app.cursor.execute(f"SELECT name FROM cams WHERE ip = '{self.local_ip}'")
        for x in app.cursor:
            self.cam_name = x[0]

        #Creating the server
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.bind(('127.0.0.1', 5000)) #Will change ip later not now bc err
        self.server.listen(10)
        self.clients = []

        self.cols = 3
        self.size = 50, 40
        self.row_default_width = 40
        self.row_default_height = 25

        self.add_empty_space(1)
        self.add_widget(Label(text = f"({self.cam_name})"))
        self.detect_people_button = Button(text = "Detect people")
        self.detect_people_button.bind(on_press = self.detect_faces)
        self.add_widget(self.detect_people_button)
        self.add_empty_space(1)

        self.cap = cv2.VideoCapture(0)
        self.cam_img = Image(source = 'cam_input.png') #Placeholder incase nothing is detected
        self.add_widget(self.cam_img)

        def update_camera(inst): #Works!
            _, f = self.cap.read()
            if _:
                f = cv2.flip(f, 0) #Flipped for some reason
                f = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
                f = cv2.resize(f, (320, 240)) #For aspect ratio
                f_bytes = f.tobytes()
                new_texture = Texture.create(size = (f.shape[1], f.shape[0])) #Inverted for some reason
                new_texture.blit_buffer(f_bytes, bufferfmt = 'ubyte')
                self.cam_img.texture = new_texture

                #Sending the data to clients
                flat_f = f.reshape((320*240*3,)).tobytes()
                for client in self.clients:
                    client.send(flat_f)

        def handle_clients(client):
            while True:
                recv = client.recv(1024).decode('utf-8')
                if recv == 'Show faces':
                    self.detect_faces('inst')

        #Since waiting for clients interrupts the thread
        def accept_clients():
            while True:
                try:
                    client, addr = self.server.accept()
                    if client not in self.clients:
                        self.clients.append(client)
                        clthread = threading.Thread(target = handle_clients, args = [client])
                        clthread.start()
                except Exception as e:
                    print(e)

        accept_client_thread = threading.Thread(target = accept_clients)
        accept_client_thread.start()

        self.faces_label = Label(text = "Nobody Found")
        self.add_widget(self.faces_label)
        self.add_empty_space(1)
        self.add_person_box = TextInput(multiline = False)
        self.add_widget(self.add_person_box)
        self.add_person_button = Button(text = 'Add person by path')
        self.add_person_button.bind(on_press = self.add_person)
        self.add_widget(self.add_person_button)

        Clock.schedule_interval(update_camera, 1/60) #Updates the camera, used for concurrent updating
        #1/60 is how many seconds before another frame


    def add_person(self, instance):
        ppath = self.add_person_box.text
        should_continue = True
        if os.path.isfile(ppath):
            person = ppath.split('/')[-1].split('.')[0]
            app.cursor.execute(f"SELECT personname FROM people WHERE camname = '{self.cam_name}'")
            for x in app.cursor:
                if len(x) > 0:
                    self.add_person_box.text = 'Already Used'
                    should_continue = False

            if should_continue:
                img_arr = cv2.imread(ppath)
                face = MTCNN().detect_faces(img_arr)
                if len(face) < 1:
                    self.add_person_box.text = "Invalid Image"
                else:
                    x, y, w, h = tuple(face[0]['box'])
                    cropped_face = cv2.resize(img_arr[y : y+h, x : x+w], (240, 240))
                    #Since many databases just store paths to the image, that's what I will do
                    cv2.imwrite(ppath, cropped_face)
                    app.cursor.execute(f"INSERT INTO people (camname, personname, path) VALUES ('{self.cam_name}', '{person}', '{ppath}')")
                    app.db.commit()
                    self.add_person_box.text = f"Saved as {person}"

                    #This method is clunky and takes a while, but seeing adding people is occasional, it's alright
        else:
            self.add_person_box.text = 'Invalid Path'

    def add_empty_space(self, c):
        for _ in range(c):
            self.add_widget(Label(text = ''))

    #For detecting the faces
    def detect_faces(self, inst):
        _, f = self.cap.read()
        if _:
            imgs, names = [], []
            app.cursor.execute(
                f"SELECT personname, path FROM people WHERE camname = '{self.cam_name}'"
            )
            for name, pth in app.cursor:
                img = cv2.imread(pth)
                imgs.append(img)
                names.append(name)
            detected = return_marked_image_with_status(f, imgs, names, 0.4)
            self.faces_label.text = '(Last Recorded)\n' + detected
            #Sending this info to app for updating
            txt = '(Last Recorded)\n' + detected; txt = txt.encode('utf-8')
            for client in self.clients:
                client.send(txt)
        else:
            self.faces_label.text = 'Camera Error'
        

        

class RedirectPage(GridLayout): #Empty Page to redirect existing users
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.local_ip = socket.gethostbyname(socket.gethostname())
        self.cam_exists = False
        app.cursor.execute('SELECT ip FROM cams')
        for x in app.cursor:
            if self.local_ip in x:
                self.cam_exists = True
        if self.cam_exists:
            app.screen_manager.current = 'Display'
        else:
            app.screen_manager.current = 'Make_Cam'

class CamApp(App):
    def build(self):
        self.db = mysql.connector.connect(
            host = 'localhost',
            user = 'root',
            passwd = 'Rb878425!',
            database = 'camdb'
        )
        self.cursor = self.db.cursor()

        self.screen_manager = ScreenManager()

        self.display_page = DisplayPage()
        display = Screen(name = 'Display')
        display.add_widget(self.display_page)
        self.screen_manager.add_widget(display)

        self.make_cam_page = MakeCamPage()
        make_cam = Screen(name = 'Make_Cam')
        make_cam.add_widget(self.make_cam_page)
        self.screen_manager.add_widget(make_cam)

        self.redir_page = RedirectPage()
        redir = Screen(name = 'Redir')
        redir.add_widget(self.redir_page)
        self.screen_manager.add_widget(redir)

        return self.screen_manager

app = CamApp()
app.run()
