import math
import os
import json
import random
import sys
import git
import magnum as mn

import numpy as np
import habitat_sim
from habitat_sim.utils import viz_utils as vut
import imageio
from PIL import Image
import multiprocessing
from functools import partial

if "google.colab" in sys.modules:
    os.environ["IMAGEIO_FFMPEG_EXE"] = "/usr/bin/ffmpeg"


repo = git.Repo(".", search_parent_directories=True)
data_path = "../Data"
output_path = "test/"
json_path = "../Data/Multi-Human-Annotations/human_motion.json"

def remove_all_objects(sim):
    for id_ in sim.get_existing_object_ids():
        sim.remove_object(id_)

def place_agent(sim, position, rotation):
    agent_state = habitat_sim.AgentState()
    #TODO annotate the parameters for overview
    agent_state.rotation = np.quaternion(-0.0, 0.7071067811865476, -0.0, -0.7071067811865475)
    position = [position[0], position[1], position[2]]
    agent_state.position = position
    agent = sim.initialize_agent(0, agent_state)
    return agent.scene_node.transformation_matrix()

def make_configuration(scene_id):
    backend_cfg = habitat_sim.SimulatorConfiguration()
    backend_cfg.gpu_device_id = 0
    backend_cfg.scene_id = scene_id
    print(backend_cfg.scene_id)
    assert os.path.exists(backend_cfg.scene_id)
    backend_cfg.enable_physics = True

    camera_resolution = [700, 900]

    sensors = {
        "view1": {
            "sensor_type": habitat_sim.SensorType.COLOR,
            "resolution": camera_resolution,
            "position": [1.5, 0.77, 0],
            "orientation": [0, -np.pi/2, np.pi],
        },
        "view2": {
            "sensor_type": habitat_sim.SensorType.COLOR,
            "resolution": camera_resolution,
            "position": [-1.5, 0.77, 0],
            "orientation": [0, np.pi/2, np.pi],
        },
        "view3": {
            "sensor_type": habitat_sim.SensorType.COLOR,
            "resolution": camera_resolution,
            "position": [0, 0.77, 1.5],
            "orientation": [0, 0, np.pi],

        },
        "view4": {
            "sensor_type": habitat_sim.SensorType.COLOR,
            "resolution": camera_resolution,
            "position": [0, 0.77, -1.5],
            "orientation": [0, np.pi, np.pi],
        },
        "view5": {
            "sensor_type": habitat_sim.SensorType.COLOR,
            "resolution": camera_resolution,
            "position": [0, -1.5, 0],
            "orientation": [-np.pi/2, 0, np.pi],
        },
        "view6": {
            "sensor_type": habitat_sim.SensorType.COLOR,
            "resolution": camera_resolution,
            "position": [1.5, -1.5, 1.5],
            "orientation": [-np.pi/6, -np.pi/4, np.pi],
        },
        "view7": {
            "sensor_type": habitat_sim.SensorType.COLOR,
            "resolution": camera_resolution,
            "position": [-1.5, -1.5, 1.5],
            "orientation": [-np.pi/6, np.pi/4, np.pi],
        },
        "view8": {
            "sensor_type": habitat_sim.SensorType.COLOR,
            "resolution": camera_resolution,
            "position": [-1.5, -1.5, -1.5],
            "orientation": [-np.pi/6, -np.pi/4 + np.pi, np.pi],
        },
        "view9": {
            "sensor_type": habitat_sim.SensorType.COLOR,
            "resolution": camera_resolution,
            "position": [1.5, -1.5, -1.5],
            "orientation": [-np.pi/6, np.pi/4 + np.pi, np.pi],
        },
    }

    sensor_specs = []
    for sensor_uuid, sensor_params in sensors.items():
        sensor_spec = habitat_sim.SensorSpec()
        sensor_spec.uuid = sensor_uuid
        sensor_spec.sensor_type = sensor_params["sensor_type"]
        sensor_spec.resolution = sensor_params["resolution"]
        sensor_spec.position = sensor_params["position"]
        sensor_spec.orientation = sensor_params["orientation"]
        sensor_specs.append(sensor_spec)

    agent_cfg = habitat_sim.agent.AgentConfiguration()
    agent_cfg.sensor_specifications = sensor_specs

    return habitat_sim.Configuration(backend_cfg, [agent_cfg])

def process(scan, viewpoints):
    viewpoints = viewpoints[scan]
    count = 0
    scene_id = os.path.join(data_path, f"scene_datasets/mp3d/{scan}/{scan}.glb")

        
    cfg = make_configuration(scene_id)

    sim = habitat_sim.Simulator(cfg)
        
    for point_id, v in viewpoints.items():
        # count += 1
        try:
            translations = v['translation']
            rotations = v['rotation']
        except:
            continue
                
        # if os.path.exists(save_path):
        #     continue
        
        v['category'] = v['category'].replace(' ', '_').replace('/', '_')
        category = v['category']
        index = v['index']
        
        rotation_quat = mn.Quaternion.rotation(mn.Deg(rotations[0][0]), mn.Vector3(1.0, 0.0, 0.0)) * \
                    mn.Quaternion.rotation(mn.Deg(rotations[0][1]), mn.Vector3(0.0, 1.0, 0.0)) * \
                    mn.Quaternion.rotation(mn.Deg(rotations[0][2]), mn.Vector3(0.0, 0.0, 1.0))
        place_agent(sim, translations[0], rotation_quat)
        
        object_template_ids = []
        obj_templates_mgr = sim.get_object_template_manager()
        glb_folder_path = os.path.join(f"{data_path}/HAPS2_0/{category}_{index}/")   
        glb_files = load_glb_files(glb_folder_path)
        glb_files.sort()
        
        for glb_file in glb_files:
            template_id = obj_templates_mgr.load_configs(glb_file)[0]
            object_template_ids.append(template_id)
                
        # translation = np.array(translation)
        # object_id = sim.add_object(object_template_ids[0])
        # sim.set_translation(translation, object_id)
        frames1, frames2, frames3 = [], [], []
        for frame_id, (template_id, translation, rotation) in enumerate(zip(object_template_ids, translations, rotations)):
            frame1, frame2, frame3 = add_object_and_capture_frame(sim, template_id, translation, rotation)
            frames1.append(frame1)
            frames2.append(frame2)
            frames3.append(frame3)
        
        if not os.path.exists(f"{output_path}/{scan}/{point_id}"):
            os.makedirs(f"{output_path}/{scan}/{point_id}")
            
        for k, frames in enumerate([frames1, frames2, frames3]):
            with imageio.get_writer(f"{output_path}/{scan}/{point_id}/{k}.mp4", fps=25) as writer:
                for frame in frames:
                    writer.append_data(frame)
    sim.close()


def simulate(sim, dt=1.0, get_frames=True):
    print("Simulating " + str(dt) + " world seconds.")
    observations = []
    start_time = sim.get_world_time()
    while sim.get_world_time() < start_time + dt:
        sim.step_physics(1.0 / 60.0)
        if get_frames:
            observations.append(sim.get_sensor_observations())
    return observations

def add_object_and_capture_frame(sim, object_template_id, translation, rotation_euler):
    # Convert Euler angles to magnum quaternion
    rotation_quat = mn.Quaternion.rotation(mn.Deg(rotation_euler[0]), mn.Vector3(1.0, 0.0, 0.0)) * \
                    mn.Quaternion.rotation(mn.Deg(rotation_euler[1]), mn.Vector3(0.0, 1.0, 0.0)) * \
                    mn.Quaternion.rotation(mn.Deg(rotation_euler[2]), mn.Vector3(0.0, 0.0, 1.0))
    
    object_id = sim.add_object(object_template_id)
    sim.set_translation(translation, object_id)
    sim.set_rotation(rotation_quat, object_id)

    sim.step_physics(1.0 / 60.0)
    
    # place_agent(sim, translation, rotation_quat)
    
    observations = sim.get_sensor_observations()
    # frame = observations["rgba_camera_fixed"]
    views = ['view1', 'view2', 'view3', 'view4', 'view5', 'view6', 'view7', 'view8', 'view9']
    frames = []
    for v in views:
        frame = observations[v]
        frame = Image.fromarray(frame).convert("RGB")
        # imageio.imwrite(f"{save_path}/{vp_id}_{v}.jpg", frame)
        frames.append(frame)
    frame1_ = np.concatenate((frames[0], frames[1]), axis=0)
    frame2_ = np.concatenate((frames[2], frames[3]), axis=0)
    frames1 = np.concatenate((frame1_, frame2_), axis=1)
    frame1_ = np.concatenate((frames[5], frames[6]), axis=0)
    frame2_ = np.concatenate((frames[7], frames[8]), axis=0)
    frames2 = np.concatenate((frame1_, frame2_), axis=1)
    sim.remove_object(object_id)

    return frames1, frames2, np.array(frames[4])

def load_glb_files(base_path):
    """Recursively load all .glb files from the given base_path"""
    glb_files = []
    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith(".glb"):
                glb_files.append(os.path.join(root, file))
    return glb_files

def dump_to_json(file_path, scan, humanpoint_id, category, index, translations, rotations):
    # If the JSON file exists, read the content
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    # Check if the scan ID exists
    if scan not in data:
        data[scan] = {}

    # Check if the humanpoint_id exists, if it exists, update it, otherwise add a new entry
    if humanpoint_id in data[scan]:
        print(f"Updating existing entry for scan {scan}, humanpoint_id {humanpoint_id}")
    else:
        print(f"Adding new entry for scan {scan}, humanpoint_id {humanpoint_id}")
        data[scan][humanpoint_id] = {}

    # Update the information under humanpoint_id: category, index, translation, and rotation
    data[scan][humanpoint_id] = {
        "category": category,
        "index": index,
        "translation": translations,
        "rotation": rotations
    }

    # Write the updated data back to the file
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Data dumped to {file_path} successfully!")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    # parser.add_argument("--scan", type=str, required=True, help="Specify the scan ID")
    parser.add_argument("--no-show-video", dest="show_video", action="store_false")
    parser.add_argument("--no-make-video", dest="make_video", action="store_false")
    parser.set_defaults(show_video=True, make_video=True)
    args, _ = parser.parse_known_args()

    show_video = args.show_video
    make_video = args.make_video


    with open(json_path, 'r') as file:
        human_motion_data = json.load(file)

    if not os.path.exists(output_path):
        os.mkdir(output_path)
        
    with multiprocessing.Pool(processes=1) as pool:  

        process_scan_partial = partial(process,
                                       viewpoints=human_motion_data)   
        scans = list(human_motion_data.keys())
        pool.map(process_scan_partial, scans)
