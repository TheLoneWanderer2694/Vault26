import obspython as obs

# Configuration settings exposed to OBS UI
source_name = ""
phrases = [
    "Welcome to the stream!",
    "Hit that follow button!",
    "Enjoy the gameplay!"
]

# Script state variables
current_phrase_idx = 0
current_char_idx = 0
frame_counter = 0
animation_speed = 5  # Lower = faster typing, Higher = slower typing
pause_counter = 0
is_pausing = False

def script_description():
    return "Animate a standard OBS Text Source with a typing/ticker effect natively using Python."

def script_properties():
    props = obs.obs_properties_add(
        
    )
    
    # Dropdown to select existing text sources in your OBS project
    p = obs.obs_properties_add_list(
        props, 
        "source_name", 
        "Text Source to Animate", 
        obs.OBS_COMBO_TYPE_EDITABLE, 
        obs.OBS_COMBO_FORMAT_STRING
    )
    
    sources = obs.obs_enum_sources()
    if sources:
        for source in sources:
            source_id = obs.obs_source_get_id(source)
            # Find GDI+ or Freetype2 text sources
            if source_id == "text_gdiplus" or source_id == "text_ft2_source":
                name = obs.obs_source_get_name(source)
                obs.obs_property_list_add_string(p, name, name)
        obs.obs_source_list_release(sources)
        
    return props

def script_update(settings):
    global source_name
    source_name = obs.obs_data_get_string(settings, "source_name")

def script_tick(seconds):
    global current_phrase_idx, current_char_idx, frame_counter, pause_counter, is_pausing
    
    if not source_name:
        return

    frame_counter += 1
    if frame_counter < animation_speed:
        return
    frame_counter = 0

    target_phrase = phrases[current_phrase_idx]

    # Handle pause when sentence is fully typed out
    if is_pausing:
        pause_counter += 1
        if pause_counter > 30:  # Pause length before switching text
            is_pausing = False
            pause_counter = 0
            current_char_idx = 0
            current_phrase_idx = (current_phrase_idx + 1) % len(phrases)
        return

    # Advance typing character by character
    current_char_idx += 1
    displayed_text = target_phrase[:current_char_idx]
    
    # Update the actual text source in OBS
    source = obs.obs_get_source_by_name(source_name)
    if source:
        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "text", displayed_text)
        obs.obs_source_update(source, settings)
        obs.obs_data_release(settings)
        obs.obs_source_release(source)

    # Check if the whole phrase has been typed
    if current_char_idx >= len(target_phrase):
        is_pausing = True