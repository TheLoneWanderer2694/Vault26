import obspython as obs
import math
import time

source_name = ""
duration = 1.0
easing_type = 0  
NUM_LOCATIONS = 5

locations = [
    (0.0, 0.0, 1.0, 1.0, 0.0),
    (500.0, 0.0, 1.0, 1.0, 0.0),
    (500.0, 500.0, 1.0, 1.0, 0.0),
    (0.0, 500.0, 1.0, 1.0, 0.0),
    (250.0, 250.0, 1.0, 1.0, 0.0)
]

target_slot = 0  
animating = False
start_x, start_y, start_sx, start_sy, start_rot = 0.0, 0.0, 1.0, 1.0, 0.0
target_x, target_y, target_sx, target_sy, target_rot = 0.0, 0.0, 1.0, 1.0, 0.0
start_time = 0.0
current_scene_item = None

hotkey_ids = [None] * NUM_LOCATIONS
saved_settings = None

def script_description():
    return "<b>Wild & Crazy OBS Move Animator</b><br/>Packed with chaotic, over-the-top, and physics-defying animation curves."

def script_properties():
    props = obs.obs_properties_create()
    
    source_prop = obs.obs_properties_add_list(
        props, "source_name", "Source Name", 
        obs.OBS_COMBO_TYPE_EDITABLE, obs.OBS_COMBO_FORMAT_STRING
    )
    current_scene_source = obs.obs_frontend_get_current_scene()
    if current_scene_source:
        scene = obs.obs_scene_from_source(current_scene_source)
        items = obs.obs_scene_enum_items(scene)
        if items:
            for item in items:
                source = obs.obs_sceneitem_get_source(item)
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(source_prop, name, name)
        obs.obs_source_release(current_scene_source)

    obs.obs_properties_add_float(props, "duration", "Transition Duration (s)", 0.1, 10.0, 0.1)
    
    ease_prop = obs.obs_properties_add_list(
        props, "easing_type", "Transition Effect Style", 
        obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT
    )
    
    effects = [
        "Smoothstep (Standard Ease)",
        "Linear (Constant)",
        "Quad In", "Quad Out", "Quad In-Out",
        "Cubic In", "Cubic Out", "Cubic In-Out",
        "Quart Out", "Quint Out",
        "Sine In", "Sine Out", "Sine In-Out",
        "Expo In", "Expo Out", "Expo In-Out",
        "Circ In", "Circ Out", "Circ In-Out",
        "Back In", "Back Out (Overshoot)", "Back In-Out",
        "Elastic In", "Elastic Out (Spring Snap)", "Elastic In-Out",
        "Bounce In", "Bounce Out (Bounce)", "Bounce In-Out",
        # --- WILD & CRAZY STYLES ---
        "Crazy Glitch Jump (Jitter)",
        "Over-The-Top Earthquake Shake",
        "Aggressive Rubber Band Snap",
        "Hyperbolic Quantum Teleport",
        "Drunken Stumble Wander",
        "Mad Scientist Double-Bounce",
        "Rollercoaster Loop-De-Loop"
    ]
    
    for idx, name in enumerate(effects):
        obs.obs_property_list_add_int(ease_prop, name, idx)

    slot_prop = obs.obs_properties_add_list(
        props, "target_slot", "Active Slot Target", 
        obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT
    )
    for i in range(NUM_LOCATIONS):
        obs.obs_property_list_add_int(slot_prop, f"Location {i+1}", i)
    
    obs.obs_properties_add_button(props, "capture_btn", "Capture Current Transform & Rotation", capture_source_transform)
    
    return props

def script_update(settings):
    global source_name, duration, easing_type, target_slot, saved_settings
    saved_settings = settings
    source_name = obs.obs_data_get_string(settings, "source_name")
    duration = max(obs.obs_data_get_double(settings, "duration"), 0.1)
    easing_type = int(obs.obs_data_get_int(settings, "easing_type"))
    target_slot = obs.obs_data_get_int(settings, "target_slot")

def script_load(settings):
    global hotkey_ids, locations
    for i in range(NUM_LOCATIONS):
        hotkey_name = f"move_loc{i+1}_hotkey"
        hotkey_desc = f"Move, Resize & Rotate: Go To Location {i+1}"
        
        x = obs.obs_data_get_double(settings, f"stored_x{i+1}")
        y = obs.obs_data_get_double(settings, f"stored_y{i+1}")
        sx = obs.obs_data_get_double(settings, f"stored_sx{i+1}")
        sy = obs.obs_data_get_double(settings, f"stored_sy{i+1}")
        rot = obs.obs_data_get_double(settings, f"stored_rot{i+1}")
        
        if sx > 0 and sy > 0:
            locations[i] = (x, y, sx, sy, rot)

        hotkey_ids[i] = obs.obs_hotkey_register_frontend(
            hotkey_name, hotkey_desc, 
            lambda pressed, idx=i: hotkey_pressed(pressed, locations[idx][0], locations[idx][1], locations[idx][2], locations[idx][3], locations[idx][4])
        )
        
        ha = obs.obs_data_get_array(settings, f"hotkey_{i+1}")
        obs.obs_hotkey_load(hotkey_ids[i], ha)
        obs.obs_data_array_release(ha)

def script_save(settings):
    global hotkey_ids, locations
    for i in range(NUM_LOCATIONS):
        obs.obs_data_set_double(settings, f"stored_x{i+1}", locations[i][0])
        obs.obs_data_set_double(settings, f"stored_y{i+1}", locations[i][1])
        obs.obs_data_set_double(settings, f"stored_sx{i+1}", locations[i][2])
        obs.obs_data_set_double(settings, f"stored_sy{i+1}", locations[i][3])
        obs.obs_data_set_double(settings, f"stored_rot{i+1}", locations[i][4])
        
        if hotkey_ids[i]:
            ha = obs.obs_hotkey_save(hotkey_ids[i])
            obs.obs_data_set_array(settings, f"hotkey_{i+1}", ha)
            obs.obs_data_array_release(ha)

def hotkey_pressed(pressed, tx, ty, tsx, tsy, trot):
    if pressed:
        trigger_move(tx, ty, tsx, tsy, trot)

def capture_source_transform(props, p):
    global saved_settings, locations
    current_scene_source = obs.obs_frontend_get_current_scene()
    if not current_scene_source:
        return
        
    scene = obs.obs_scene_from_source(current_scene_source)
    item = obs.obs_scene_find_source_recursive(scene, source_name)
    obs.obs_source_release(current_scene_source)

    if not item:
        obs.script_log(obs.LOG_WARNING, f"Source '{source_name}' not found for transform capture.")
        return

    transform = obs.obs_transform_info()
    obs.obs_sceneitem_get_info2(item, transform)
    
    cur_x = transform.pos.x
    cur_y = transform.pos.y
    cur_sx = transform.scale.x
    cur_sy = transform.scale.y
    cur_rot = transform.rot

    locations[target_slot] = (cur_x, cur_y, cur_sx, cur_sy, cur_rot)
    
    if saved_settings:
        obs.obs_data_set_double(saved_settings, f"stored_x{target_slot+1}", cur_x)
        obs.obs_data_set_double(saved_settings, f"stored_y{target_slot+1}", cur_y)
        obs.obs_data_set_double(saved_settings, f"stored_sx{target_slot+1}", cur_sx)
        obs.obs_data_set_double(saved_settings, f"stored_sy{target_slot+1}", cur_sy)
        obs.obs_data_set_double(saved_settings, f"stored_rot{target_slot+1}", cur_rot)
        
    obs.script_log(obs.LOG_INFO, f"Captured position, scale, and rotation ({cur_rot}°) into Location {target_slot+1}.")

def trigger_move(tx, ty, tsx, tsy, trot):
    global animating, start_x, start_y, start_sx, start_sy, start_rot, target_x, target_y, target_sx, target_sy, target_rot, start_time, current_scene_item
    
    if animating:
        return

    current_scene_source = obs.obs_frontend_get_current_scene()
    if not current_scene_source:
        return
        
    scene = obs.obs_scene_from_source(current_scene_source)
    current_scene_item = obs.obs_scene_find_source_recursive(scene, source_name)
    obs.obs_source_release(current_scene_source)

    if not current_scene_item:
        obs.script_log(obs.LOG_WARNING, f"Source '{source_name}' not found.")
        return

    transform = obs.obs_transform_info()
    obs.obs_sceneitem_get_info2(current_scene_item, transform)
    
    start_x = transform.pos.x
    start_y = transform.pos.y
    start_sx = transform.scale.x
    start_sy = transform.scale.y
    start_rot = transform.rot
    
    target_x, target_y = tx, ty
    target_sx, target_sy = tsx, tsy
    target_rot = trot
    
    start_time = time.time()
    animating = True
    obs.timer_add(animate_tick, 16)

def bounce_ease(p):
    n1 = 7.5625
    d1 = 2.75
    if p < 1 / d1:
        return n1 * p * p
    elif p < 2 / d1:
        p -= 1.5 / d1
        return n1 * p * p + 0.75
    elif p < 2.5 / d1:
        p -= 2.25 / d1
        return n1 * p * p + 0.9375
    else:
        p -= 2.625 / d1
        return n1 * p * p + 0.984375

def calculate_ease(p, mode):
    if mode == 0:   # Smoothstep
        return p * p * (3.0 - 2.0 * p)
    elif mode == 1: # Linear
        return p
    elif mode == 2: # Quad In
        return p * p
    elif mode == 3: # Quad Out
        return p * (2.0 - p)
    elif mode == 4: # Quad In-Out
        return 2.0 * p * p if p < 0.5 else -1.0 + (4.0 - 2.0 * p) * p
    elif mode == 5: # Cubic In
        return p * p * p
    elif mode == 6: # Cubic Out
        f = p - 1.0
        return f * f * f + 1.0
    elif mode == 7: # Cubic In-Out
        return 4.0 * p * p * p if p < 0.5 else 1.0 - math.pow(-2.0 * p + 2.0, 3.0) / 2.0
    elif mode == 8: # Quart Out
        f = p - 1.0
        return 1.0 - f * f * f * f
    elif mode == 9: # Quint Out
        f = p - 1.0
        return 1.0 + f * f * f * f * f
    elif mode == 10: # Sine In
        return 1.0 - math.cos((p * math.pi) / 2.0)
    elif mode == 11: # Sine Out
        return math.sin((p * math.pi) / 2.0)
    elif mode == 12: # Sine In-Out
        return 0.5 * (1.0 - math.cos(math.pi * p))
    elif mode == 13: # Expo In
        return 0.0 if p == 0.0 else math.pow(2.0, 10.0 * (p - 1.0))
    elif mode == 14: # Expo Out
        return 1.0 if p == 1.0 else 1.0 - math.pow(2.0, -10.0 * p)
    elif mode == 15: # Expo In-Out
        if p == 0.0: return 0.0
        if p == 1.0: return 1.0
        return math.pow(2.0, 20.0 * p - 10.0) / 2.0 if p < 0.5 else (2.0 - math.pow(2.0, -20.0 * p + 10.0)) / 2.0
    elif mode == 16: # Circ In
        return 1.0 - math.sqrt(1.0 - math.pow(p, 2.0))
    elif mode == 17: # Circ Out
        return math.sqrt(1.0 - math.pow(p - 1.0, 2.0))
    elif mode == 18: # Circ In-Out
        return (1.0 - math.sqrt(1.0 - math.pow(2.0 * p, 2.0))) / 2.0 if p < 0.5 else (math.sqrt(1.0 - math.pow(-2.0 * p + 2.0, 2.0)) + 1.0) / 2.0
    elif mode == 19: # Back In
        c1 = 1.70158
        c3 = c1 + 1.0
        return c3 * p * p * p - c1 * p * p
    elif mode == 20: # Back Out
        c1 = 1.70158
        c3 = c1 + 1.0
        return 1.0 + c3 * math.pow(p - 1.0, 3.0) + c1 * math.pow(p - 1.0, 2.0)
    elif mode == 21: # Back In-Out
        c1 = 1.70158
        c2 = c1 * 1.525
        return (math.pow(2.0 * p, 2.0) * ((c2 + 1.0) * 2.0 * p - c2)) / 2.0 if p < 0.5 else (math.pow(2.0 * p - 2.0, 2.0) * ((c2 + 1.0) * (p * 2.0 - 2.0) + c2) + 2.0) / 2.0
    elif mode == 22: # Elastic In
        c4 = (2.0 * math.pi) / 3.0
        return 0.0 if p == 0.0 else (1.0 if p == 1.0 else -math.pow(2.0, 10.0 * p - 10.0) * math.sin((p * 10.0 - 10.75) * c4))
    elif mode == 23: # Elastic Out
        c4 = (2.0 * math.pi) / 3.0
        return 0.0 if p == 0.0 else (1.0 if p == 1.0 else math.pow(2.0, -10.0 * p) * math.sin((p * 10.0 - 0.75) * c4) + 1.0)
    elif mode == 24: # Elastic In-Out
        c5 = (2.0 * math.pi) / 4.5
        return 0.0 if p == 0.0 else (1.0 if p == 1.0 else (-(math.pow(2.0, 20.0 * p - 10.0) * math.sin((20.0 * p - 11.125) * c5)) / 2.0 if p < 0.5 else (math.pow(2.0, -20.0 * p + 10.0) * math.sin((20.0 * p - 11.125) * c5)) / 2.0 + 1.0))
    elif mode == 25: # Bounce In
        return 1.0 - bounce_ease(1.0 - p)
    elif mode == 26: # Bounce Out
        return bounce_ease(p)
    elif mode == 27: # Bounce In-Out
        return (1.0 - bounce_ease(1.0 - 2.0 * p)) / 2.0 if p < 0.5 else (1.0 + bounce_ease(2.0 * p - 1.0)) / 2.0
    # --- WILD & CRAZY IMPLEMENTATIONS ---
    elif mode == 28: # Crazy Glitch Jump (Jitter)
        base = p * p * (3.0 - 2.0 * p)
        jitter = math.sin(p * 45.0) * 0.08 * (1.0 - p)
        return max(0.0, min(1.0, base + jitter))
    elif mode == 29: # Over-The-Top Earthquake Shake
        base = p * p * (3.0 - 2.0 * p)
        shake = math.sin(p * 80.0) * 0.15 * math.sin(p * math.pi)
        return max(0.0, min(1.0, base + shake))
    elif mode == 30: # Aggressive Rubber Band Snap
        return p + math.sin(p * math.pi * 5.0) * 0.25 * (1.0 - p)
    elif mode == 31: # Hyperbolic Quantum Teleport
        return 0.0 if p < 0.5 else 1.0
    elif mode == 32: # Drunken Stumble Wander
        base = p * p * (3.0 - 2.0 * p)
        stumble = math.sin(p * math.pi * 3.5) * 0.2 * math.sin(p * math.pi)
        return max(0.0, min(1.0, base + stumble))
    elif mode == 33: # Mad Scientist Double-Bounce
        if p < 0.5:
            return 2.0 * p * p
        else:
            p2 = (p - 0.5) * 2.0
            return 1.0 + (math.sin(p2 * math.pi * 3.0) * 0.2 * (1.0 - p2))
    elif mode == 34: # Rollercoaster Loop-De-Loop
        base = p * p * (3.0 - 2.0 * p)
        loop = math.sin(p * math.pi * 2.0) * 0.35 * math.sin(p * math.pi)
        return base + loop
    else:
        return p * p * (3.0 - 2.0 * p)

def animate_tick():
    global animating, current_scene_item, start_x, start_y, start_sx, start_sy, start_rot, target_x, target_y, target_sx, target_sy, target_rot, start_time, duration, easing_type

    if not animating:
        return

    elapsed = time.time() - start_time
    progress = elapsed / duration

    if progress >= 1.0:
        progress = 1.0
        animating = False
        obs.timer_remove(animate_tick)

    ease_progress = calculate_ease(progress, easing_type)
    
    # Extra crazy positional multiplier for glitch/shake modes to make them visibly explosive
    extra_shake_x = 0.0
    extra_shake_y = 0.0
    if easing_type == 28 or easing_type == 29: # Glitch or Earthquake
        extra_shake_x = math.sin(progress * 120.0) * 15.0 * (1.0 - progress)
        extra_shake_y = math.cos(progress * 110.0) * 15.0 * (1.0 - progress)

    new_x = start_x + (target_x - start_x) * ease_progress + extra_shake_x
    new_y = start_y + (target_y - start_y) * ease_progress + extra_shake_y
    new_sx = start_sx + (target_sx - start_sx) * ease_progress
    new_sy = start_sy + (target_sy - start_sy) * ease_progress
    new_rot = start_rot + (target_rot - start_rot) * ease_progress

    if easing_type == 34: # Rollercoaster Loop rotation twist kick
        new_rot += math.sin(progress * math.pi * 2.0) * 45.0

    if current_scene_item:
        transform = obs.obs_transform_info()
        obs.obs_sceneitem_get_info2(current_scene_item, transform)
        transform.pos.x = new_x
        transform.pos.y = new_y
        transform.scale.x = new_sx
        transform.scale.y = new_sy
        transform.rot = new_rot
        obs.obs_sceneitem_set_info2(current_scene_item, transform)

    if not animating:
        current_scene_item = None