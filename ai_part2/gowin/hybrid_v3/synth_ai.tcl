# Standalone synthesis only. No pin assignment or board programming.
set root [file normalize [file dirname [info script]]]
cd $root
set_device GW1NR-LV9QN88PC6/I5 -device_version C
add_file [file join $root src ai_core_model_v3.v]
add_file [file join $root constraints ai_core.sdc]
set_option -top_module ai_core
set_option -output_base_name ai_core_v3
run syn
