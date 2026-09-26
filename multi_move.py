import obspython as obs
import math
import time

active_animations = []
NUM_LOCATIONS = 5
managed_sources = {}
saved_settings = None

def script_description():
    return "<b>Multi-Source Wild & Crazy OBS Move Animator + Per-Slot Size & Layers</b><br/>Animate multiple OBS sources with independent slot sizing, layer ordering, and auto-tracking."

def script_properties():
    props = obs.obs_properties_create()
    
    source_prop = obs.obs_properties_add_list(
        props, "source_name", "Primary Managed Source Name", 
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
        "Smoothstep (Standard Ease)", "Linear (Constant)",
        "Quad In", "Quad Out", "Quad In-Out",
        "Cubic In", "Cubic Out", "Cubic In-Out",
        "Quart Out", "Quint Out",
        "Sine In", "Sine Out", "Sine In-Out",
        "Expo In", "Expo Out", "Expo In-Out",
        "Circ In", "Circ Out", "Circ In-Out",
        "Back In", "Back Out (Overshoot)", "Back In-Out",
        "Elastic In", "Elastic Out (Spring Snap)", "Elastic In-Out",
        "Bounce In", "Bounce Out (Bounce)", "Bounce In-Out",
        "Crazy Glitch Jump (Jitter)", "Over-The-Top Earthquake Shake",
        "Aggressive Rubber Band Snap", "Hyperbolic Quantum Teleport",
        "Drunken Stumble Wander", "Mad Scientist Double-Bounce",
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
        
    layer_prop = obs.obs_properties_add_list(
        props, "target_layer_action", "Layer Action for Active Slot",
        obs.OBS_COMBO_TYPE_LIST, obs.OBS_COMBO_FORMAT_INT
    )
    obs.obs_property_list_add_int(layer_prop, "Don't Change Layer", -1)
    obs.obs_property_list_add_int(layer_prop, "Move to Top of Stack", 0)
    obs.obs_property_list_add_int(layer_prop, "Move to Bottom of Stack", 1)
    obs.obs_property_list_add_int(layer_prop, "Move Up One Layer", 2)
    obs.obs_property_list_add_int(layer_prop, "Move Down One Layer", 3)

    obs.obs_properties_add_bool(props, "auto_capture_resize", "Auto-Update Slot When Source is Resized/Moved")
    obs.obs_properties_add_button(props, "capture_btn", "Capture Current Transform, Rotation & Layer to Slot", capture_source_transform)
    return props

def script_update(settings):
    global saved_settings
    saved_settings = settings
    s_name = obs.obs_data_get_string(settings, "source_name")
    
    if s_name not in managed_sources:
        managed_sources[s_name] = {
            "locations": [(0.0, 0.0, 1.0, 1.0, 0.0, -1)] * NUM_LOCATIONS,
            "target_slot": 0, "duration": 1.0, "easing_type": 0,
            "hotkey_ids": [None] * NUM_LOCATIONS,
            "trigger_hotkey_id": None,
            "last_transform": (0, 0, 0, 0, 0)
        }
    
    managed_sources[s_name]["duration"] = max(obs.obs_data_get_double(settings, "duration"), 0.1)
    managed_sources[s_name]["easing_type"] = int(obs.obs_data_get_int(settings, "easing_type"))
    managed_sources[s_name]["target_slot"] = int(obs.obs_data_get_int(settings, "target_slot"))
    managed_sources[s_name]["auto_capture"] = obs.obs_data_get_bool(settings, "auto_capture_resize")

    # If layer action changes via dropdown, immediately update the active slot's layer memory
    target_slot = managed_sources[s_name]["target_slot"]
    new_layer = int(obs.obs_data_get_int(settings, "target_layer_action"))
    cur_loc = managed_sources[s_name]["locations"][target_slot]
    managed_sources[s_name]["locations"][target_slot] = (cur_loc[0], cur_loc[1], cur_loc[2], cur_loc[3], cur_loc[4], new_layer)

def script_load(settings):
    s_name = obs.obs_data_get_string(settings, "source_name")
    if not s_name:
        return

    if s_name not in managed_sources:
        managed_sources[s_name] = {
            "locations": [(0.0, 0.0, 1.0, 1.0, 0.0, -1)] * NUM_LOCATIONS,
            "target_slot": 0, "duration": 1.0, "easing_type": 0,
            "hotkey_ids": [None] * NUM_LOCATIONS,
            "trigger_hotkey_id": None,
            "last_transform": (0, 0, 0, 0, 0)
        }

    locs = managed_sources[s_name]["locations"]
    hotkeys = managed_sources[s_name]["hotkey_ids"]

    for i in range(NUM_LOCATIONS):
        hotkey_name = f"move_{s_name}_loc{i+1}_hotkey"
        hotkey_desc = f"[{s_name}] Go To Location {i+1}"
        
        x = obs.obs_data_get_double(settings, f"{s_name}_stored_x{i+1}")
        y = obs.obs_data_get_double(settings, f"{s_name}_stored_y{i+1}")
        sx = obs.obs_data_get_double(settings, f"{s_name}_stored_sx{i+1}")
        sy = obs.obs_data_get_double(settings, f"{s_name}_stored_sy{i+1}")
        rot = obs.obs_data_get_double(settings, f"{s_name}_stored_rot{i+1}")
        layer = obs.obs_data_get_int(settings, f"{s_name}_stored_layer{i+1}")
        
        # Default uninitialized layers to -1 (Don't Change)
        if layer == 0 and not obs.obs_data_has_user_value(settings, f"{s_name}_stored_layer{i+1}"):
            layer = -1
        
        if sx > 0 and sy > 0:
            locs[i] = (x, y, sx, sy, rot, layer)

        hotkeys[i] = obs.obs_hotkey_register_frontend(
            hotkey_name, hotkey_desc, 
            lambda pressed, name=s_name, idx=i: hotkey_pressed(pressed, name, idx)
        )
        
        ha = obs.obs_data_get_array(settings, f"{s_name}_hotkey_{i+1}")
        obs.obs_hotkey_load(hotkeys[i], ha)
        obs.obs_data_array_release(ha)

    trigger_hkey_name = f"move_{s_name}_trigger_active_slot"
    trigger_hkey_desc = f"[{s_name}] Trigger Active Target Slot"
    
    managed_sources[s_name]["trigger_hotkey_id"] = obs.obs_hotkey_register_frontend(
        trigger_hkey_name, trigger_hkey_desc,
        lambda pressed, name=s_name: trigger_active_slot_hotkey(pressed, name)
    )
    tha = obs.obs_data_get_array(settings, f"{s_name}_trigger_hotkey")
    obs.obs_hotkey_load(managed_sources[s_name]["trigger_hotkey_id"], tha)
    obs.obs_data_array_release(tha)
    
    obs.timer_add(check_source_transforms, 500)

def script_unload():
    obs.timer_remove(check_source_transforms)

def script_save(settings):
    for s_name, data in managed_sources.items():
        locs = data["locations"]
        hotkeys = data["hotkey_ids"]
        for i in range(NUM_LOCATIONS):
            obs.obs_data_set_double(settings, f"{s_name}_stored_x{i+1}", locs[i][0])
            obs.obs_data_set_double(settings, f"{s_name}_stored_y{i+1}", locs[i][1])
            obs.obs_data_set_double(settings, f"{s_name}_stored_sx{i+1}", locs[i][2])
            obs.obs_data_set_double(settings, f"{s_name}_stored_sy{i+1}", locs[i][3])
            obs.obs_data_set_double(settings, f"{s_name}_stored_rot{i+1}", locs[i][4])
            obs.obs_data_set_int(settings, f"{s_name}_stored_layer{i+1}", locs[i][5])
            
            if hotkeys[i]:
                ha = obs.obs_hotkey_save(hotkeys[i])
                obs.obs_data_set_array(settings, f"{s_name}_hotkey_{i+1}", ha)
                obs.obs_data_array_release(ha)
                
        if data["trigger_hotkey_id"]:
            tha = obs.obs_hotkey_save(data["trigger_hotkey_id"])
            obs.obs_data_set_array(settings, f"{s_name}_trigger_hotkey", tha)
            obs.obs_data_array_release(tha)

def hotkey_pressed(pressed, source_name, loc_idx):
    if pressed and source_name in managed_sources:
        locs = managed_sources[source_name]["locations"]
        tx, ty, tsx, tsy, trot, layer_action = locs[loc_idx]
        dur = managed_sources[source_name]["duration"]
        ease = managed_sources[source_name]["easing_type"]
        trigger_move_multi(source_name, tx, ty, tsx, tsy, trot, layer_action, dur, ease)

def trigger_active_slot_hotkey(pressed, source_name):
    if pressed and source_name in managed_sources:
        data = managed_sources[source_name]
        slot_idx = data["target_slot"]
        locs = data["locations"]
        tx, ty, tsx, tsy, trot, layer_action = locs[slot_idx]
        dur = data["duration"]
        ease = data["easing_type"]
        trigger_move_multi(source_name, tx, ty, tsx, tsy, trot, layer_action, dur, ease)

def capture_source_transform(props, p):
    global saved_settings, managed_sources
    if not saved_settings:
        return
    source_name = obs.obs_data_get_string(saved_settings, "source_name")
    if not source_name:
        return

    current_scene_source = obs.obs_frontend_get_current_scene()
    if not current_scene_source:
        return
        
    scene = obs.obs_scene_from_source(current_scene_source)
    item = obs.obs_scene_find_source_recursive(scene, source_name)
    obs.obs_source_release(current_scene_source)

    if not item:
        return

    transform = obs.obs_transform_info()
    obs.obs_sceneitem_get_info2(item, transform)
    
    cur_x, cur_y = transform.pos.x, transform.pos.y
    cur_sx, cur_sy = transform.scale.x, transform.scale.y
    cur_rot = transform.rot
    layer_action = int(obs.obs_data_get_int(saved_settings, "target_layer_action"))

    if source_name not in managed_sources:
        script_update(saved_settings)
    
    target_slot = managed_sources[source_name]["target_slot"]
    managed_sources[source_name]["locations"][target_slot] = (cur_x, cur_y, cur_sx, cur_sy, cur_rot, layer_action)
    
    obs.obs_data_set_double(saved_settings, f"{source_name}_stored_x{target_slot+1}", cur_x)
    obs.obs_data_set_double(saved_settings, f"{source_name}_stored_y{target_slot+1}", cur_y)
    obs.obs_data_set_double(saved_settings, f"{source_name}_stored_sx{target_slot+1}", cur_sx)
    obs.obs_data_set_double(saved_settings, f"{source_name}_stored_sy{target_slot+1}", cur_sy)
    obs.obs_data_set_double(saved_settings, f"{source_name}_stored_rot{target_slot+1}", cur_rot)
    obs.obs_data_set_int(saved_settings, f"{source_name}_stored_layer{target_slot+1}", layer_action)

def check_source_transforms():
    global saved_settings, managed_sources
    if not saved_settings:
        return
        
    for source_name, data in managed_sources.items():
        if not data.get("auto_capture", False):
            continue
            
        current_scene_source = obs.obs_frontend_get_current_scene()
        if not current_scene_source:
            continue
            
        scene = obs.obs_scene_from_source(current_scene_source)
        item = obs.obs_scene_find_source_recursive(scene, source_name)
        obs.obs_source_release(current_scene_source)

        if not item:
            continue

        transform = obs.obs_transform_info()
        obs.obs_sceneitem_get_info2(item, transform)
        
        current_t = (transform.pos.x, transform.pos.y, transform.scale.x, transform.scale.y, transform.rot)
        if current_t != data["last_transform"]:
            data["last_transform"] = current_t
            target_slot = data["target_slot"]
            current_layer = data["locations"][target_slot][5]
            data["locations"][target_slot] = (current_t[0], current_t[1], current_t[2], current_t[3], current_t[4], current_layer)
            
            obs.obs_data_set_double(saved_settings, f"{source_name}_stored_x{target_slot+1}", current_t[0])
            obs.obs_data_set_double(saved_settings, f"{source_name}_stored_y{target_slot+1}", current_t[1])
            obs.obs_data_set_double(saved_settings, f"{source_name}_stored_sx{target_slot+1}", current_t[2])
            obs.obs_data_set_double(saved_settings, f"{source_name}_stored_sy{target_slot+1}", current_t[3])
            obs.obs_data_set_double(saved_settings, f"{source_name}_stored_rot{target_slot+1}", current_t[4])

def trigger_move_multi(source_name, tx, ty, tsx, tsy, trot, layer_action, duration, easing_type):
    global active_animations
    current_scene_source = obs.obs_frontend_get_current_scene()
    if not current_scene_source:
        return
        
    scene = obs.obs_scene_from_source(current_scene_source)
    scene_item = obs.obs_scene_find_source_recursive(scene, source_name)
    obs.obs_source_release(current_scene_source)

    if not scene_item:
        return

    if layer_action == 0:
        obs.obs_sceneitem_set_order(scene_item, obs.OBS_ORDER_MOVE_TOP)
    elif layer_action == 1:
        obs.obs_sceneitem_set_order(scene_item, obs.OBS_ORDER_MOVE_BOTTOM)
    elif layer_action == 2:
        obs.obs_sceneitem_set_order(scene_item, obs.OBS_ORDER_MOVE_UP)
    elif layer_action == 3:
        obs.obs_sceneitem_set_order(scene_item, obs.OBS_ORDER_MOVE_DOWN)

    transform = obs.obs_transform_info()
    obs.obs_sceneitem_get_info2(scene_item, transform)
    
    anim_data = {
        "scene_item": scene_item, "source_name": source_name,
        "start_x": transform.pos.x, "start_y": transform.pos.y,
        "start_sx": transform.scale.x, "start_sy": transform.scale.y,
        "start_rot": transform.rot,
        "target_x": tx, "target_y": ty, "target_sx": tsx, "target_sy": tsy, "target_rot": trot,
        "duration": duration, "easing_type": easing_type, "start_time": time.time()
    }

    active_animations = [a for a in active_animations if a["source_name"] != source_name]
    active_animations.append(anim_data)

    if len(active_animations) == 1:
        obs.timer_add(animate_tick_multi, 16)

def bounce_ease(p):
    n1, d1 = 7.5625, 2.75
    if p < 1 / d1: return n1 * p * p
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
    if mode == 0: return p * p * (3.0 - 2.0 * p)
    elif mode == 1: return p
    elif mode == 2: return p * p
    elif mode == 3: return p * (2.0 - p)
    elif mode == 4: return 2.0 * p * p if p < 0.5 else -1.0 + (4.0 - 2.0 * p) * p
    elif mode == 5: return p * p * p
    elif mode == 6: 
        f = p - 1.0
        return f * f * f + 1.0
    elif mode == 7: return 4.0 * p * p * p if p < 0.5 else 1.0 - math.pow(-2.0 * p + 2.0, 3.0) / 2.0
    elif mode == 8: 
        f = p - 1.0
        return 1.0 - f * f * f * f
    elif mode == 9: 
        f = p - 1.0
        return 1.0 + f * f * f * f * f
    elif mode == 10: return 1.0 - math.cos((p * math.pi) / 2.0)
    elif mode == 11: return math.sin((p * math.pi) / 2.0)
    elif mode == 12: return 0.5 * (1.0 - math.cos(math.pi * p))
    elif mode == 13: return 0.0 if p == 0.0 else math.pow(2.0, 10.0 * (p - 1.0))
    elif mode == 14: return 1.0 if p == 1.0 else 1.0 - math.pow(2.0, -10.0 * p)
    elif mode == 15: 
        if p == 0.0: return 0.0
        if p == 1.0: return 1.0
        return math.pow(2.0, 20.0 * p - 10.0) / 2.0 if p < 0.5 else (2.0 - math.pow(2.0, -20.0 * p + 10.0)) / 2.0
    elif mode == 16: return 1.0 - math.sqrt(1.0 - math.pow(p, 2.0))
    elif mode == 17: return math.sqrt(1.0 - math.pow(p - 1.0, 2.0))
    elif mode == 18: return (1.0 - math.sqrt(1.0 - math.pow(2.0 * p, 2.0))) / 2.0 if p < 0.5 else (math.sqrt(1.0 - math.pow(-2.0 * p + 2.0, 2.0)) + 1.0) / 2.0
    elif mode == 19: 
        c1 = 1.70158
        return (c1 + 1.0) * p * p * p - c1 * p * p
    elif mode == 20: 
        c1 = 1.70158
        return 1.0 + (c1 + 1.0) * math.pow(p - 1.0, 3.0) + c1 * math.pow(p - 1.0, 2.0)
    elif mode == 21: 
        c2 = 1.70158 * 1.525
        return (math.pow(2.0 * p, 2.0) * ((c2 + 1.0) * 2.0 * p - c2)) / 2.0 if p < 0.5 else (math.pow(2.0 * p - 2.0, 2.0) * ((c2 + 1.0) * (p * 2.0 - 2.0) + c2) + 2.0) / 2.0
    elif mode == 22: 
        c4 = (2.0 * math.pi) / 3.0
        return 0.0 if p == 0.0 else (1.0 if p == 1.0 else -math.pow(2.0, 10.0 * p - 10.0) * math.sin((p * 10.0 - 10.75) * c4))
    elif mode == 23: 
        c4 = (2.0 * math.pi) / 3.0
        return 0.0 if p == 0.0 else (1.0 if p == 1.0 else math.pow(2.0, -10.0 * p) * math.sin((p * 10.0 - 0.75) * c4) + 1.0)
    elif mode == 24: 
        c5 = (2.0 * math.pi) / 4.5
        return 0.0 if p == 0.0 else (1.0 if p == 1.0 else (-(math.pow(2.0, 20.0 * p - 10.0) * math.sin((20.0 * p - 11.125) * c5)) / 2.0 if p < 0.5 else (math.pow(2.0, -20.0 * p + 10.0) * math.sin((20.0 * p - 11.125) * c5)) / 2.0 + 1.0))
    elif mode == 25: return 1.0 - bounce_ease(1.0 - p)
    elif mode == 26: return bounce_ease(p)
    elif mode == 27: return (1.0 - bounce_ease(1.0 - 2.0 * p)) / 2.0 if p < 0.5 else (1.0 + bounce_ease(2.0 * p - 1.0)) / 2.0
    elif mode == 28: 
        base = p * p * (3.0 - 2.0 * p)
        return max(0.0, min(1.0, base + math.sin(p * 45.0) * 0.08 * (1.0 - p)))
    elif mode == 29: 
        base = p * p * (3.0 - 2.0 * p)
        return max(0.0, min(1.0, base + math.sin(p * 80.0) * 0.15 * math.sin(p * math.pi)))
    elif mode == 30: return p + math.sin(p * math.pi * 5.0) * 0.25 * (1.0 - p)
    elif mode == 31: return 0.0 if p < 0.5 else 1.0
    elif mode == 32: 
        base = p * p * (3.0 - 2.0 * p)
        return max(0.0, min(1.0, base + math.sin(p * math.pi * 3.5) * 0.2 * math.sin(p * math.pi)))
    elif mode == 33: 
        if p < 0.5: return 2.0 * p * p
        else:
            p2 = (p - 0.5) * 2.0
            return 1.0 + (math.sin(p2 * math.pi * 3.0) * 0.2 * (1.0 - p2))
    elif mode == 34: 
        base = p * p * (3.0 - 2.0 * p)
        return base + math.sin(p * math.pi * 2.0) * 0.35 * math.sin(p * math.pi)
    else:
        return p * p * (3.0 - 2.0 * p)

def animate_tick_multi():
    global active_animations
    if not active_animations:
        obs.timer_remove(animate_tick_multi)
        return

    now = time.time()
    still_active = []

    for anim in active_animations:
        elapsed = now - anim["start_time"]
        progress = elapsed / anim["duration"]

        if progress >= 1.0:
            progress = 1.0
        else:
            still_active.append(anim)

        ease_progress = calculate_ease(progress, anim["easing_type"])
        
        extra_shake_x, extra_shake_y = 0.0, 0.0
        if anim["easing_type"] in [28, 29]:
            extra_shake_x = math.sin(progress * 120.0) * 15.0 * (1.0 - progress)
            extra_shake_y = math.cos(progress * 110.0) * 15.0 * (1.0 - progress)

        new_x = anim["start_x"] + (anim["target_x"] - anim["start_x"]) * ease_progress + extra_shake_x
        new_y = anim["start_y"] + (anim["target_y"] - anim["start_y"]) * ease_progress + extra_shake_y
        new_sx = anim["start_sx"] + (anim["target_sx"] - anim["start_sx"]) * ease_progress
        new_sy = anim["start_sy"] + (anim["target_sy"] - anim["start_sy"]) * ease_progress
        new_rot = anim["start_rot"] + (anim["target_rot"] - anim["start_rot"]) * ease_progress

        if anim["easing_type"] == 34:
            new_rot += math.sin(progress * math.pi * 2.0) * 45.0

        if anim["scene_item"]:
            transform = obs.obs_transform_info()
            obs.obs_sceneitem_get_info2(anim["scene_item"], transform)
            transform.pos.x = new_x
            transform.pos.y = new_y
            transform.scale.x = new_sx
            transform.scale.y = new_sy
            transform.rot = new_rot
            obs.obs_sceneitem_set_info2(anim["scene_item"], transform)

    active_animations = still_active
    if not active_animations:
        obs.timer_remove(animate_tick_multi)