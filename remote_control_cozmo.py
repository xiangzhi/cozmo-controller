#!/usr/bin/env python3

# Copyright (c) 2016 Anki, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License in the file LICENSE.txt or at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''Control Cozmo using a webpage on your computer.

This example lets you control Cozmo by Remote Control, using a webpage served by Flask.
'''

import json
import sys

from remote_cozmo_wrapper import RemoteControlCozmo
from cozmo.util import degrees, distance_mm, speed_mmps

from designed_actions import DesignedBehaviors


sys.path.append('lib/')
import flask_helpers
import cozmo


try:
    from flask import Flask, request, render_template
except ImportError:
    sys.exit("Cannot import from flask: Do `pip3 install --user flask` to install")

try:
    from PIL import Image, ImageDraw
except ImportError:
    sys.exit("Cannot import from PIL: Do `pip3 install --user Pillow` to install")


DEBUG_ANNOTATIONS_DISABLED = 0
DEBUG_ANNOTATIONS_ENABLED_VISION = 1
DEBUG_ANNOTATIONS_ENABLED_ALL = 2


# Annotator for displaying RobotState (position, etc.) on top of the camera feed
class RobotStateDisplay(cozmo.annotate.Annotator):
    def apply(self, image, scale):
        d = ImageDraw.Draw(image)

        bounds = [3, 0, image.width, image.height]

        def print_line(text_line):
            text = cozmo.annotate.ImageText(text_line, position=cozmo.annotate.TOP_LEFT, color='lightblue')
            text.render(d, bounds)
            TEXT_HEIGHT = 11
            bounds[1] += TEXT_HEIGHT

        robot = self.world.robot

        # Display the Pose info for the robot

        pose = robot.pose
        print_line('Pose: Pos = <%.1f, %.1f, %.1f>' % pose.position.x_y_z)
        print_line('Pose: Rot quat = <%.1f, %.1f, %.1f, %.1f>' % pose.rotation.q0_q1_q2_q3)
        print_line('Pose: angle_z = %.1f' % pose.rotation.angle_z.degrees)
        print_line('Pose: origin_id: %s' % pose.origin_id)

        # Display the Accelerometer and Gyro data for the robot

        print_line('Accelmtr: <%.1f, %.1f, %.1f>' % robot.accelerometer.x_y_z)
        print_line('Gyro: <%.1f, %.1f, %.1f>' % robot.gyro.x_y_z)


def create_default_image(image_width, image_height, do_gradient=False):
    '''Create a place-holder PIL image to use until we have a live feed from Cozmo'''
    image_bytes = bytearray([0x70, 0x70, 0x70]) * image_width * image_height

    if do_gradient:
        i = 0
        for y in range(image_height):
            for x in range(image_width):
                image_bytes[i] = int(255.0 * (x / image_width))   # R
                image_bytes[i+1] = int(255.0 * (y / image_height))  # G
                image_bytes[i+2] = 0                                # B
                i += 3

    image = Image.frombytes('RGB', (image_width, image_height), bytes(image_bytes))
    return image


flask_app = Flask(__name__,static_url_path='/static')
remote_control_cozmo = None
_default_camera_image = create_default_image(320, 240)
_is_mouse_look_enabled_by_default = False

_display_debug_annotations = DEBUG_ANNOTATIONS_ENABLED_ALL


def remap_to_range(x, x_min, x_max, out_min, out_max):
    '''convert x (in x_min..x_max range) to out_min..out_max range'''
    if x < x_min:
        return out_min
    elif x > x_max:
        return out_max
    else:
        ratio = (x - x_min) / (x_max - x_min)
        return out_min + ratio * (out_max - out_min)



def get_anim_sel_drop_down(selectorIndex):
    html_text = '''<select onchange="handleDropDownSelect(this)" name="animSelector''' + str(selectorIndex) + '''">'''
    i = 0
    for anim_name in remote_control_cozmo.anim_names:
        is_selected_item = (i == remote_control_cozmo.anim_index_for_key[selectorIndex])
        selected_text = ''' selected="selected"''' if is_selected_item else ""
        html_text += '''<option value=''' + str(i) + selected_text + '''>''' + anim_name + '''</option>'''
        i += 1
    html_text += '''</select>'''
    return html_text


def get_anim_sel_drop_downs():
    html_text = ""
    for i in range(10):
        # list keys 1..9,0 as that's the layout on the keyboard
        key = i+1 if (i<9) else 0
        html_text += str(key) + ''': ''' + get_anim_sel_drop_down(key) + '''<br>'''
    return html_text


def to_js_bool_string(bool_value):
    return "true" if bool_value else "false"


@flask_app.route("/")
def handle_index_page():

    battery_level = "low" if (remote_control_cozmo.cozmo.battery_voltage < 3.5) else "normal"
    return render_template('index.html',battery_level=battery_level)



@flask_app.route('/updateCozmo', methods=['POST'])
def handle_updateCozmo():
    '''Called very frequently from Javascript to provide an update loop'''
    if remote_control_cozmo:
        remote_control_cozmo.update()
    return ""


@flask_app.route("/cozmoImage")
def handle_cozmoImage():
    '''Called very frequently from Javascript to request the latest camera image'''
    if remote_control_cozmo:
        image = remote_control_cozmo.cozmo.world.latest_image
        if image:
            if _display_debug_annotations != DEBUG_ANNOTATIONS_DISABLED:
                image = image.annotate_image(scale=2)
            else:
                image = image.raw_image

            return flask_helpers.serve_pil_image(image)
    return flask_helpers.serve_pil_image(_default_camera_image)


def handle_key_event(key_request, is_key_down):
    message = json.loads(key_request.data.decode("utf-8"))
    if remote_control_cozmo:
        remote_control_cozmo.handle_key(key_code=(message['keyCode']), is_shift_down=message['hasShift'],
                                        is_ctrl_down=message['hasCtrl'], is_alt_down=message['hasAlt'],
                                        is_key_down=is_key_down)
    return ""


@flask_app.route('/mousemove', methods=['POST'])
def handle_mousemove():
    '''Called from Javascript whenever mouse moves'''
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        remote_control_cozmo.handle_mouse(mouse_x=(message['clientX']), mouse_y=message['clientY'],
                                          delta_x=message['deltaX'], delta_y=message['deltaY'],
                                          is_button_down=message['isButtonDown'])
    return ""


@flask_app.route('/setMouseLookEnabled', methods=['POST'])
def handle_setMouseLookEnabled():
    '''Called from Javascript whenever mouse-look mode is toggled'''
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        remote_control_cozmo.set_mouse_look_enabled(is_mouse_look_enabled=message['isMouseLookEnabled'])
    return ""


@flask_app.route('/setHeadlightEnabled', methods=['POST'])
def handle_setHeadlightEnabled():
    '''Called from Javascript whenever headlight is toggled on/off'''
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        remote_control_cozmo.cozmo.set_head_light(enable=message['isHeadlightEnabled'])
    return ""


@flask_app.route('/setAreDebugAnnotationsEnabled', methods=['POST'])
def handle_setAreDebugAnnotationsEnabled():
    '''Called from Javascript whenever debug-annotations mode is toggled'''
    message = json.loads(request.data.decode("utf-8"))
    global _display_debug_annotations
    _display_debug_annotations = message['areDebugAnnotationsEnabled']
    if remote_control_cozmo:
        if _display_debug_annotations == DEBUG_ANNOTATIONS_ENABLED_ALL:
            remote_control_cozmo.cozmo.world.image_annotator.enable_annotator('robotState')
        else:
            remote_control_cozmo.cozmo.world.image_annotator.disable_annotator('robotState')
    return ""


@flask_app.route('/setFreeplayEnabled', methods=['POST'])
def handle_setFreeplayEnabled():
    '''Called from Javascript whenever freeplay mode is toggled on/off'''
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        isFreeplayEnabled = message['isFreeplayEnabled']
        if isFreeplayEnabled:
            remote_control_cozmo.cozmo.start_freeplay_behaviors()
        else:
            remote_control_cozmo.cozmo.stop_freeplay_behaviors()
    return ""


@flask_app.route('/keydown', methods=['POST'])
def handle_keydown():
    '''Called from Javascript whenever a key is down (note: can generate repeat calls if held down)'''
    return handle_key_event(request, is_key_down=True)


@flask_app.route('/keyup', methods=['POST'])
def handle_keyup():
    '''Called from Javascript whenever a key is released'''
    return handle_key_event(request, is_key_down=False)


@flask_app.route('/dropDownSelect', methods=['POST'])
def handle_dropDownSelect():
    '''Called from Javascript whenever an animSelector dropdown menu is selected (i.e. modified)'''
    message = json.loads(request.data.decode("utf-8"))

    item_name_prefix = "animSelector"
    item_name = message['itemName']

    if remote_control_cozmo and item_name.startswith(item_name_prefix):
        item_name_index = int(item_name[len(item_name_prefix):])
        remote_control_cozmo.set_anim(item_name_index, message['selectedIndex'])

    return ""




@flask_app.route('/sayText', methods=['POST'])
def handle_sayText():
    '''Called from Javascript whenever the saytext text field is modified'''
    message = json.loads(request.data.decode("utf-8"))
    if remote_control_cozmo:
        remote_control_cozmo.text_to_say = message['textEntered']
    return ""

db = DesignedBehaviors()
last_behavior = None

def _stop_action():
    global last_behavior
    if(last_behavior and last_behavior.is_active):
        last_behavior.stop()
        last_behavior = None

@flask_app.route('/get_action_list', methods=['POST'])
def handle_getActionList():
    db_list = db._get_action_list()
    json_str = json.dumps(db_list)
    return json_str

@flask_app.route('/special_action', methods=['POST'])
def handle_ourAction():
    action_name = request.args.get('action')
    print("running action {}".format(action_name))
    _stop_action()
    global last_behavior
    last_behavior = db._run_action(action_name, remote_control_cozmo.cozmo)
    return "" 


@flask_app.route('/stop_action', methods=['POST'])
def handle_stopActions():
    #this will stop the most recent action 
    _stop_action()
    return ""

@flask_app.route('/special_actions', methods=['POST'])
def handle_ourActions():
    #real with what kind of action we want it do
    print(request.data)
    message = json.loads(request.data.decode("utf-8"))
    action_num = int(message['action_num'])

    if(action_num == 1):
        pass

    if(action_num == 1):
        global last_behavior
        last_behavior = remote_control_cozmo.cozmo.start_behavior(cozmo.behavior.BehaviorTypes.RollBlock)
    else:
        if(last_behavior and last_behavior.is_active):
            last_behavior.stop()
            last_behavior = None
    return ""

    # if remote_control_cozmo:
    #     remote_control_cozmo.say_text("Doing action {}".format(message['action_num']))
    # return ""   


@flask_app.route('/getDebugInfo', methods=['POST'])
def handle_getDebugInfo():
    if remote_control_cozmo:
        action_queue_text = ""
        i = 1
        for action in remote_control_cozmo.action_queue:
            action_queue_text += str(i) + ": " + remote_control_cozmo.action_to_text(action) + "<br>"
            i += 1

        return '''Action Queue:<br>''' + action_queue_text + '''
        '''
    return ""


def run(sdk_conn):
    robot = sdk_conn.wait_for_robot()
    robot.world.image_annotator.add_annotator('robotState', RobotStateDisplay)

    global remote_control_cozmo
    remote_control_cozmo = RemoteControlCozmo(robot)

    # Turn on image receiving by the camera
    robot.camera.image_stream_enabled = True

    flask_helpers.run_flask(flask_app)

if __name__ == '__main__':
    cozmo.setup_basic_logging()
    cozmo.robot.Robot.drive_off_charger_on_connect = False  # RC can drive off charger if required
    try:
        cozmo.connect(run)
    except cozmo.ConnectionError as e:
        sys.exit("A connection error occurred: %s" % e)
