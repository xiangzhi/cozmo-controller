__author__ = 'Prerna Chikersal'
import cozmo
import time
from cozmo.util import degrees, distance_mm, speed_mmps
import random
import yaml


class DesignedBehaviors(object):

    def __init__(self):
        with open('actions.yaml') as file:
            self._anim_obj = yaml.load(file)

    def _get_action_list(self):
        action_list = dir(self)
        action_list = [s for s in action_list if not s.startswith('_')]
        return action_list

    def _run_action(self, action_name, robot):
        return getattr(self, action_name)(robot)

    def walksquare(self, robot: cozmo.robot.Robot): ## WALKS IN A SQUARE FOR THE NO ENGAGEMENT CASE
        robot.set_robot_volume(0.1)
        sdist = 150
        s2dist = 150
        spd = 25
        while True:
            robot.drive_straight(distance_mm(sdist), speed_mmps(spd)).wait_for_completed()
            robot.turn_in_place(degrees(90)).wait_for_completed()
            robot.drive_straight(distance_mm(s2dist), speed_mmps(spd)).wait_for_completed()
            robot.turn_in_place(degrees(90)).wait_for_completed()
            robot.drive_straight(distance_mm(sdist), speed_mmps(spd)).wait_for_completed()
            robot.turn_in_place(degrees(90)).wait_for_completed()
            robot.drive_straight(distance_mm(s2dist), speed_mmps(spd)).wait_for_completed()
            robot.turn_in_place(degrees(90)).wait_for_completed()

    def peekattablet(self, robot: cozmo.robot.Robot): ## PEEKS AND REACTS TO THE USER'S TABLET ==> FOR THE HIGH ENGAGEMENT CASE
        robot.set_robot_volume(0.3)
        robot.set_head_angle(degrees(90)).wait_for_completed()
        time.sleep(1)
        action1 = robot.set_lift_height(40)
        action1.wait_for_completed()
        action3 = robot.drive_straight(distance_mm(10), speed_mmps(50))
        action3.wait_for_completed()
        action2 = robot.set_head_angle(degrees(-50), in_parallel=True)
        action2.wait_for_completed()
        robot.play_anim(name="anim_memorymatch_reacttopattern_standard_01").wait_for_completed()
        robot.drive_straight(distance_mm(-10), speed_mmps(50)).wait_for_completed()


    def _play_anim_wrapper(self, robot, anim_list):
        robot.set_robot_volume(0.3)
        selected_anim = random.choice(anim_list)
        robot.play_anim(name=selected_anim).wait_for_completed()
        robot.play_anim(name="anim_neutral_eyes_01").wait_for_completed()
        robot.set_lift_height(0.0).wait_for_completed()        

    def WrongGuess(self, robot: cozmo.robot.Robot): ## REACTS TO BAD OUTCOME ==> FOR THE HIGH ENGAGEMENT CASE

        _list = self._anim_obj["WrongGuess"] 
        self._play_anim_wrapper(robot, _list)

    def WrongLevel(self, robot: cozmo.robot.Robot): ## REACTS TO BAD OUTCOME ==> FOR THE HIGH ENGAGEMENT CASE

        _list = self._anim_obj["WrongLevel"] 
        self._play_anim_wrapper(robot, _list)

    def CorrectGuess(self, robot: cozmo.robot.Robot): ## REACTS TO GOOD OUTCOME ==> FOR THE HIGH ENGAGEMENT CASE
       
        _list = self._anim_obj["CorrectGuess"] 
        self._play_anim_wrapper(robot, _list)

    def CorrectLevel(self, robot: cozmo.robot.Robot): ## REACTS TO GOOD OUTCOME ==> FOR THE HIGH ENGAGEMENT CASE
        
        _list = self._anim_obj["CorrectLevel"] 
        self._play_anim_wrapper(robot, _list)        

    def EngageUser(self, robot: cozmo.robot.Robot): ## ENGAGES USER  ==> FOR THE MEDIUM ENGAGEMENT CASE
        
        _list = self._anim_obj["EngageUser"] 
        self._play_anim_wrapper(robot, _list)

    def LearnIdle(self, robot: cozmo.robot.Robot): ## ENGAGES USER  ==> FOR THE MEDIUM ENGAGEMENT CASE
        _list = self._anim_obj["LearnIdle"] 
        self._play_anim_wrapper(robot, _list)

    def lookaround(self, robot: cozmo.robot.Robot):
        robot.set_robot_volume(0.1)
        return robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)

    def rollblock(self, robot: cozmo.robot.Robot):
        robot.set_robot_volume(0.1)
        return robot.start_behavior(cozmo.behavior.BehaviorTypes.RollBlock)

#     def rollblock(self, robot: cozmo.robot.Robot):
#         lookaround = robot.start_behavior(cozmo.behavior.BehaviorTypes.LookAroundInPlace)
# #     cubes = robot.world.wait_until_observe_num_objects(num=1, object_type=cozmo.objects.LightCube, timeout=60)
#     lookaround.stop()

#     if len(cubes) == 1:
#         roll = robot.start_behavior(cozmo.behavior.BehaviorTypes.RollBlock)
#         start_time = time.time()
#         while(roll.is_active):
#             if(time.time() - start_time >= 60):
#                 roll.stop()
#             time.sleep(0.5)

# def cozmo_program(self, robot: cozmo.robot.Robot):
#     badoutcome(robot)
#     #walksquare(robot)
#     #bobj = czrollblocks(robot)
#     #print (bobj)
#     # sttime = time.time()
#     # stoprollblocks(robot, bobj)
#     # entime = time.time()
#     # if entime-sttime>10:
#     #     stoprollblocks()



# cozmo.run_program(cozmo_program)